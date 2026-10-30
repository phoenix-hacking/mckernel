"""In-memory protocol tests; no real process, filesystem custody or observer."""
import copy
import unittest
from unittest import mock
import custody_protocol as c

class Protocol(unittest.TestCase):
    def setUp(self):
        self.nonce='a'*32
        self.parent={'pid':10,'birth':100,'ppid':2,'pgid':10,'sid':2}
        self.child={'pid':11,'birth':101,'ppid':10,'pgid':10,'sid':2}
        self.state=c.OuterProtocol(self.nonce,self.parent,50)
        self.calls=[]
    def accept(self, phase, child=None, observe=None, publish=None, stopped=None, clock=None, gate=None):
        event=c.make_event(self.nonce,phase,self.parent,child)
        identities={r['pid']:r for r in (self.parent,child) if r is not None}
        return self.state.accept(event,child,clock or (lambda:1),stopped or (lambda:False),
            gate or (lambda:(self.calls.append('gate') or True)),lambda:True,observe or (lambda:(identities,sorted(identities))),
            publish or (lambda record:self.calls.append(('durable',record))))
    def test_ack_after_durable_and_both_phases_exactly_once(self):
        for phase,child in (('PARENT_READY',None),('IMAGE_READY',self.child)):
            event=c.make_event(self.nonce,phase,self.parent,child)
            self.assertEqual(self.accept(phase,child),c.canonical(c.ack_for(event))+b'\n')
        self.assertEqual([x if isinstance(x,str) else x[0] for x in self.calls],['gate','durable','gate','gate','durable','gate'])
        with self.assertRaises(ValueError): self.accept('IMAGE_READY',self.child)
    def test_wrong_order_seals_unknown(self):
        with self.assertRaises(ValueError): self.accept('IMAGE_READY',self.child)
        with self.assertRaises(ValueError): self.accept('PARENT_READY')
    def test_unknown_stop_never_acknowledges(self):
        with self.assertRaises(TimeoutError): self.accept('PARENT_READY',stopped=lambda:None)
        self.assertTrue(self.state.unknown)
    def test_nonpositive_gate_never_acknowledges(self):
        for result in (False,None,0,1,{}):
            self.state=c.OuterProtocol(self.nonce,self.parent,50)
            with self.subTest(result=result), self.assertRaises(ValueError):
                self.accept('PARENT_READY',gate=lambda:result)
            self.assertTrue(self.state.unknown)
    def test_parent_rejects_gate_and_invalid_deadline_before_write(self):
        for deadline in (None,False,0,-1,float('nan'),float('inf')):
            with self.subTest(deadline=deadline), mock.patch.object(c.os,'write') as write:
                with self.assertRaises(ValueError):
                    c.parent_handshake(3,4,self.nonce,'PARENT_READY',self.parent,None,deadline,lambda:True,lambda:False)
                write.assert_not_called()
        for result in (False,None,0,1,{}):
            with self.subTest(result=result), mock.patch.object(c.os,'write') as write, mock.patch.object(c.time,'monotonic',return_value=1):
                with self.assertRaises(ValueError):
                    c.parent_handshake(3,4,self.nonce,'PARENT_READY',self.parent,None,50,lambda:result,lambda:False)
                write.assert_not_called()
    def test_image_binding_is_independent_of_event_and_held(self):
        self.accept('PARENT_READY')
        event=c.make_event(self.nonce,'IMAGE_READY',self.parent,self.child)
        wrong=dict(self.child,birth=999)
        identities={10:self.parent,11:self.child}
        with self.assertRaises(ValueError):
            self.state.accept(event,wrong,lambda:1,lambda:False,lambda:True,lambda:True,
                              lambda:(identities,[10,11]),lambda _:None)
        self.assertTrue(self.state.unknown)
        self.state=c.OuterProtocol(self.nonce,self.parent,50)
        self.accept('PARENT_READY')
        published=[]
        with self.assertRaises(ValueError):
            self.state.accept(event,self.child,lambda:1,lambda:False,lambda:True,lambda:False,
                              lambda:(identities,[10,11]),published.append)
        self.assertEqual(published,[])
        self.assertTrue(self.state.unknown)
    def test_parent_must_be_group_leader_before_event(self):
        with self.assertRaises(ValueError):
            c.make_event(self.nonce,'PARENT_READY',dict(self.parent,pgid=2),None)
    def test_untyped_census_or_identity_alias_rejected(self):
        for identities,members in (({10:self.parent},[10.0]),({10:dict(self.parent,birth=100.0)},[10])):
            self.state=c.OuterProtocol(self.nonce,self.parent,50)
            with self.assertRaises(ValueError):
                self.accept('PARENT_READY',observe=lambda:(identities,members))
            self.assertTrue(self.state.unknown)
    def test_failed_publication_never_acknowledges(self):
        def bad(_): raise OSError('fsync failed')
        with self.assertRaises(OSError): self.accept('PARENT_READY',publish=bad)
        self.assertTrue(self.state.unknown)
    def test_identity_drift_after_publication_never_acknowledges(self):
        samples=[({10:self.parent},[10]),({10:dict(self.parent,birth=999)},[10])]
        with self.assertRaises(ValueError): self.accept('PARENT_READY',observe=lambda:samples.pop(0))
        self.assertTrue(self.state.unknown)
    def test_stop_or_deadline_after_publication_never_acknowledges(self):
        for expired in ('stop','clock'):
            self.state=c.OuterProtocol(self.nonce,self.parent,50)
            ticks=iter([1,1,50 if expired=='clock' else 1])
            flags=iter([False,False,True if expired=='stop' else False])
            with self.subTest(expired=expired), self.assertRaises(TimeoutError):
                self.accept('PARENT_READY',stopped=lambda:next(flags),clock=lambda:next(ticks))
            self.assertTrue(self.state.unknown)
    def test_expiry_during_gate_prevents_event_write(self):
        ticks=iter([1,50])
        with mock.patch.object(c.os,'write') as write, mock.patch.object(c.time,'monotonic',side_effect=lambda:next(ticks)):
            with self.assertRaises(TimeoutError):
                c.parent_handshake(3,4,self.nonce,'PARENT_READY',self.parent,None,50,lambda:True,lambda:False)
            write.assert_not_called()
    def test_parent_rejects_mismatched_ack_and_never_completes(self):
        event=c.make_event(self.nonce,'PARENT_READY',self.parent,None)
        wrong=c.canonical(dict(c.ack_for(event),event_sha256='0'*64))+b'\n'
        with mock.patch.object(c.os,'write',side_effect=lambda fd,b:len(b)), mock.patch.object(c.os,'read',side_effect=[bytes([x]) for x in wrong]), mock.patch.object(c.select,'select',return_value=([4],[],[])), mock.patch.object(c.time,'monotonic',return_value=1):
            with self.assertRaises(ValueError): c.parent_handshake(3,4,self.nonce,'PARENT_READY',self.parent,None,50,lambda:True,lambda:False)
    def test_child_lineage_or_unknown_group_rejected(self):
        with self.assertRaises(ValueError): c.make_event(self.nonce,'IMAGE_READY',self.parent,dict(self.child,ppid=20))
        with self.assertRaises(ValueError): self.accept('PARENT_READY',observe=lambda:({10:self.parent},[10,99]))

if __name__=='__main__': unittest.main(verbosity=2)
