#![no_std]

use core::ffi::{c_char, c_int, c_long, c_void};
use core::panic::PanicInfo;
use core::ptr::null_mut;

const BUF_SIZE: usize = 32 * 1024;
const NALLOC: c_int = 10;
const QL_SUCCESS: c_int = 0;
const QL_NORMAL: c_int = 2;
const QL_CONTINUE: c_int = 1;
const QL_EXIT: c_int = 0;
const QL_RET_FINAL: u8 = b'F';
const QL_RET_RESUME: u8 = b'R';
const QL_COMMAND: u8 = b'0';
const QL_ARG: u8 = b'1';
const QL_ENV: u8 = b'2';
const QL_NAME_ENV: &[u8] = b"QL_NAME\0";
const QL_PARAM_ENV: &[u8] = b"QL_PARAM_PATH\0";
const QL_PARAM_EXTE: &[u8] = b".param\0";
const QL_SWAP_ENV: &[u8] = b"QL_SWAP_PATH\0";
const QL_SWAP_PATH: &[u8] = b"/tmp\0";
const HOME_ENV: &[u8] = b"HOME\0";
const FMT_S_SLASH: &[u8] = b"%s/\0";
const FMT_PARAM_FILE: &[u8] = b"%s%s%s\0";
const FMT_SWAP_FILE: &[u8] = b"%s/%s%d\0";
const READ_MODE: &[u8] = b"r\0";
const INVALID_FILE_FORMAT: &[u8] = b"invalid file format\n\0";

#[no_mangle]
pub static mut mck_ql_argc: c_int = NALLOC;
#[no_mangle]
pub static mut mck_ql_argv: *mut *mut c_char = null_mut();
#[no_mangle]
pub static mut mck_ql_env: *mut *mut c_char = null_mut();

static mut QL_NAME_BUF: [c_char; 33] = [0; 33];
static mut SWAP_FILE: [c_char; 1024] = [0; 1024];
static mut PARAM_FILE: [c_char; 1024] = [0; 1024];
static mut QL_MODE_FLG: c_int = 0;
static mut RANK: c_int = -1;
static mut BUFFER: [u8; BUF_SIZE] = [0; BUF_SIZE];
static mut QL_INITIALIZED: c_int = 0;

unsafe extern "C" {
    static mut environ: *mut *mut c_char;
    static mut stderr: *mut c_void;

    fn getenv(name: *const c_char) -> *mut c_char;
    fn strcpy(dst: *mut c_char, src: *const c_char) -> *mut c_char;
    fn sprintf(dst: *mut c_char, fmt: *const c_char, ...) -> c_int;
    fn fopen(path: *const c_char, mode: *const c_char) -> *mut c_void;
    fn fgets(s: *mut c_char, size: c_int, stream: *mut c_void) -> *mut c_char;
    fn fclose(stream: *mut c_void) -> c_int;
    fn strchr(s: *const c_char, c: c_int) -> *mut c_char;
    fn strlen(s: *const c_char) -> usize;
    fn atoi(s: *const c_char) -> c_int;
    fn malloc(size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn exit(status: c_int) -> !;
    fn fprintf(stream: *mut c_void, fmt: *const c_char, ...) -> c_int;
    fn syscall(number: c_long, ...) -> c_long;
    fn PMI_Barrier() -> c_int;

    fn qlmpi_pmpi_init(argc: *mut c_int, argv: *mut *mut *mut c_char) -> c_int;
    fn qlmpi_pmpi_init_fortran(ierr: *mut c_int);
    fn qlmpi_mpi_comm_rank_world(rank: *mut c_int) -> c_int;
    fn qlmpi_mpi_success_value() -> c_int;
}

unsafe fn freev(mut vector: *mut *mut c_char) {
    let original = vector;
    while !vector.is_null() && !(*vector).is_null() {
        free((*vector).cast());
        vector = vector.add(1);
    }
    free(original.cast());
}

fn hex_value(byte: u8) -> c_int {
    match byte {
        b'0'..=b'9' => (byte - b'0') as c_int,
        b'A'..=b'F' => (byte - b'A' + 10) as c_int,
        b'a'..=b'f' => (byte - b'a' + 10) as c_int,
        _ => 0,
    }
}

unsafe fn esc_get(input: *mut c_char, output: *mut c_char) {
    let mut p = input.cast::<u8>();
    let mut q = output.cast::<u8>();

    while *p != 0 {
        if *p == b'%' && *p.add(1) != 0 && *p.add(2) != 0 {
            let mut c = 0;
            let mut i = 0;
            while i < 2 {
                p = p.add(1);
                c <<= 4;
                c += hex_value(*p);
                i += 1;
            }
            *q = c as u8;
            q = q.add(1);
        } else {
            *q = *p;
            q = q.add(1);
        }
        p = p.add(1);
    }
    *q = 0;
}

unsafe fn swapout(fname: *mut c_char, buf: *mut c_void, size: usize, flag: c_int) -> c_int {
    syscall(801, fname, buf, size, flag) as c_int
}

unsafe fn ql_get_option() -> c_int {
    let env_str = getenv(QL_NAME_ENV.as_ptr().cast());
    if env_str.is_null() {
        0
    } else {
        strcpy((&raw mut QL_NAME_BUF).cast(), env_str);
        1
    }
}

unsafe fn ql_init() -> c_int {
    let mut tmp_path = [0 as c_char; 1024];
    let mut env_str: *mut c_char;

    if QL_INITIALIZED != 0 {
        return QL_CONTINUE;
    }

    QL_MODE_FLG = ql_get_option();
    if QL_MODE_FLG != 0 {
        qlmpi_mpi_comm_rank_world(&raw mut RANK);

        env_str = getenv(QL_PARAM_ENV.as_ptr().cast());
        if env_str.is_null() {
            sprintf(
                tmp_path.as_mut_ptr(),
                FMT_S_SLASH.as_ptr().cast(),
                getenv(HOME_ENV.as_ptr().cast()),
            );
        } else {
            sprintf(tmp_path.as_mut_ptr(), FMT_S_SLASH.as_ptr().cast(), env_str);
        }
        sprintf(
            (&raw mut PARAM_FILE).cast::<c_char>(),
            FMT_PARAM_FILE.as_ptr().cast::<c_char>(),
            tmp_path.as_ptr(),
            (&raw mut QL_NAME_BUF).cast::<c_char>(),
            QL_PARAM_EXTE.as_ptr(),
        );

        env_str = getenv(QL_SWAP_ENV.as_ptr().cast());
        if env_str.is_null() {
            strcpy(tmp_path.as_mut_ptr(), QL_SWAP_PATH.as_ptr().cast());
        } else {
            strcpy(tmp_path.as_mut_ptr(), env_str);
        }
        sprintf(
            (&raw mut SWAP_FILE).cast::<c_char>(),
            FMT_SWAP_FILE.as_ptr().cast::<c_char>(),
            tmp_path.as_ptr(),
            (&raw mut QL_NAME_BUF).cast::<c_char>(),
            RANK,
        );

        QL_INITIALIZED = 1;
        return QL_SUCCESS;
    }

    QL_INITIALIZED = 1;
    QL_NORMAL
}

#[no_mangle]
pub unsafe extern "C" fn ql_client(argc: *mut c_int, argv: *mut *mut *mut c_char) -> c_int {
    let mut ret = QL_EXIT;
    let mut buf = [0 as c_char; 4096];
    let mut envs: *mut *mut c_char = null_mut();
    let mut args: *mut *mut c_char = null_mut();
    let mut arg_cursor: *mut *mut c_char = null_mut();
    let mut env_cursor: *mut *mut c_char = null_mut();

    if QL_MODE_FLG == 0 {
        return QL_EXIT;
    }

    syscall(803);
    PMI_Barrier();

    if swapout(
        (&raw mut SWAP_FILE).cast::<c_char>(),
        (&raw mut BUFFER).cast::<c_void>(),
        BUF_SIZE,
        1,
    ) == -1
    {
        syscall(804);
        return QL_EXIT;
    }

    let fp = fopen(
        (&raw mut PARAM_FILE).cast::<c_char>(),
        READ_MODE.as_ptr().cast(),
    );
    if fp.is_null() {
        syscall(804);
        return QL_EXIT;
    }

    while !fgets(buf.as_mut_ptr(), 4096, fp).is_null() {
        let cmd = buf[0] as u8;
        let len = strlen(buf.as_ptr());
        if len != 0 {
            *buf.as_mut_ptr().add(len - 1) = 0;
        }

        if cmd == QL_COMMAND {
            let mut t = strchr(buf.as_ptr(), b'=' as c_int);
            if t.is_null() || (*t.add(1) as u8 != QL_RET_RESUME && *t.add(1) as u8 != QL_RET_FINAL)
            {
                fprintf(stderr, INVALID_FILE_FORMAT.as_ptr().cast::<c_char>());
                exit(1);
            }
            t = t.add(1);
            if *t as u8 == QL_RET_RESUME {
                ret = QL_CONTINUE;
            } else {
                ret = QL_EXIT;
            }

            t = strchr(t, b' ' as c_int);
            if !t.is_null() {
                let n = atoi(t.add(1));
                args = malloc(core::mem::size_of::<*mut c_char>() * (n as usize + 1)).cast();
                arg_cursor = args;
                t = strchr(t.add(1), b' ' as c_int);
                if !t.is_null() {
                    let env_count = atoi(t.add(1));
                    envs = malloc(core::mem::size_of::<*mut c_char>() * (env_count as usize + 1))
                        .cast();
                    env_cursor = envs;
                }
            }
        } else if cmd == QL_ARG {
            if args.is_null() {
                continue;
            }
            let mut t = strchr(buf.as_ptr(), b' ' as c_int);
            if t.is_null() {
                continue;
            }
            let n = atoi(t.add(1));
            t = strchr(t.add(1), b' ' as c_int);
            if t.is_null() {
                continue;
            }
            t = t.add(1);
            *arg_cursor = malloc(n as usize + 1).cast();
            esc_get(t, *arg_cursor);
            arg_cursor = arg_cursor.add(1);
        } else if cmd == QL_ENV {
            if envs.is_null() {
                continue;
            }
            let mut t = strchr(buf.as_ptr(), b' ' as c_int);
            if t.is_null() {
                continue;
            }
            let n = atoi(t.add(1));
            t = strchr(t.add(1), b' ' as c_int);
            if t.is_null() {
                continue;
            }
            t = t.add(1);
            *env_cursor = malloc(n as usize + 1).cast();
            esc_get(t, *env_cursor);
            env_cursor = env_cursor.add(1);
        }
    }
    fclose(fp);

    if !args.is_null() {
        *arg_cursor = null_mut();
        if !mck_ql_argv.is_null() {
            freev(mck_ql_argv);
        }
        mck_ql_argv = args;
        if !argv.is_null() {
            *argv = args;
        }

        mck_ql_argc = 0;
        while !(*mck_ql_argv.add(mck_ql_argc as usize)).is_null() {
            mck_ql_argc += 1;
        }
        if !argc.is_null() {
            *argc = mck_ql_argc;
        }
    }

    if !envs.is_null() {
        *env_cursor = null_mut();
        if !mck_ql_env.is_null() {
            freev(mck_ql_env);
        }
        mck_ql_env = envs;
        environ = envs;
    }

    syscall(804);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn MPI_Init(argc: *mut c_int, argv: *mut *mut *mut c_char) -> c_int {
    let rc = qlmpi_pmpi_init(argc, argv);
    if rc == qlmpi_mpi_success_value() {
        ql_init();
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn mpi_init_(ierr: *mut c_int) {
    qlmpi_pmpi_init_fortran(ierr);
    if !ierr.is_null() && *ierr == qlmpi_mpi_success_value() {
        ql_init();
    }
}

#[no_mangle]
pub unsafe extern "C" fn ql_client_(ierr: *mut c_int) {
    let mut argc = 0;
    let mut argv: *mut *mut c_char = null_mut();

    if !ierr.is_null() {
        *ierr = ql_client(&mut argc, &mut argv);
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}
