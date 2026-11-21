"""Extract observed native startup milestones without treating them as UI readiness."""
import re


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
        'hmi_zone_memory_attached': 'ZoneMonitor::snapshot SHM shm.items.zones.uifwk.ovip attached' in text,
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


def summarize_display(console):
    text = console.replace('\r', '')
    _, begin, remaining = text.partition('\nNAC_HMI_DISPLAY_LOG_BEGIN\n')
    display_log, end, _ = remaining.partition('\nNAC_HMI_DISPLAY_LOG_END\n')
    lines = set(display_log.splitlines()) if begin and end else set()
    report = {
        'hmi_display_probe_complete': bool(begin and end and '\nNAC_HMI_DISPLAY_END\n' in text),
        'hmi_display_launch_observed': 'NAC_HMI_DISPLAY_LAUNCH' in lines,
        'hmi_display_egl_surface_created': 'NAC_QT_PBUFFER_CREATED=800x480' in lines,
        'hmi_display_frame_captured': False,
    }
    if begin and end:
        match = re.search(r'^NAC_HMI_DISPLAY_EXIT=(\d+)$', display_log, re.MULTILINE)
        if match:
            report['hmi_display_exit_code'] = int(match[1])
    return report
