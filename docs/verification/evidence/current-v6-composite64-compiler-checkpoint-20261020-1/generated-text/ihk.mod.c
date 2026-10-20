#include <linux/module.h>
#include <linux/export-internal.h>
#include <linux/compiler.h>

MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};

KSYMTAB_FUNC(ihk_os_application_adopt_current_v4, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_application_close_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_application_invoke_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_application_open_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_create_unbooted_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_create_unbooted_v2, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_create_unbooted_v3, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_create_unbooted_v4, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_create_unbooted_v5, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_create_unbooted_v6, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_destroy_unbooted_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_service_register_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_service_unregister_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_topology_query_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_os_with_kobject_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_DATA(ihk_provider_lifecycle_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_smp_provider_attach_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_smp_provider_attach_v2, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_smp_provider_close_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_smp_provider_detach_v1, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_smp_provider_detach_v2, "_gpl", "MCKERNEL_IHK_V1");
KSYMTAB_FUNC(ihk_smp_provider_open_v1, "_gpl", "MCKERNEL_IHK_V1");

MODULE_INFO(depends, "");


MODULE_INFO(srcversion, "625CAF5A171111FF29015B7");
MODULE_INFO(rhelversion, "10.2");
