"""Extract observed native startup milestones without treating them as UI readiness."""


def summarize(console):
    text = console.replace('\r', '')
    # Restrict bus-name claims to the explicit D-Bus inventory, not log messages.
    _, begin, inventory = text.partition('\nNAC_HMI_BUS_NAMES\n')
    bus, end, _ = inventory.partition('\nNAC_HMI_BUS_NAMES_END\n')
    if not begin or not end:
        bus = ''
    return {
        'qt_offscreen_verified': '\nQT_PROBE_OK\n' in text,
        'hmi_master_started': 'UIFwkMasterProcess::main Starting' in text,
        'hmi_settings_shared_memory_created': 'SettingsSharedMemory::ctor SHM shared.hmicommon.syshmi.ovip created' in text,
        'hmi_master_constructor_message_observed': 'HMIMaster::ctor' in text,
        'hmi_master_event_loop_message_observed': 'CUIFwkMasterProcess::run: Before loop' in text,
        'hmi_master_initialization_message_observed': 'CUIFwkMasterProcess::sltHMIMasterInitialized' in text,
        'hmi_master_alive': '\nNAC_HMI_MASTER_ALIVE\n' in text,
        'native_nsm_on_bus': 'string "org.genivi.NodeStateManager"' in bus,
        'native_framework_on_bus': 'string "com.ovip.afw.ApplicationExecutionControl"' in bus,
        'native_hmi_on_bus': 'string "org.ovip.uifwk"' in bus,
        'hmi_bus_ping_verified': '\nNAC_HMI_DBUS_PING_OK\n' in text,
        'hmi_probe_complete': '\nNAC_HMI_STATE_END\n' in text,
        'rendered_frame_verified': False,
        'hmi_frame_verified': False,
    }
