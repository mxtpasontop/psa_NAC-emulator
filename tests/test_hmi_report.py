"""Startup reports must distinguish an observation from an initialized HMI."""
from pathlib import Path
import sys
import subprocess
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from hmi_report import summarize, summarize_display


class HmiReportTests(unittest.TestCase):
    def test_display_report_only_attributes_egl_to_the_native_display_process(self):
        unrelated = '\nNAC_QT_PBUFFER_CREATED=800x480\n'
        display_log = ('\nNAC_HMI_DISPLAY_LOG_BEGIN\r\nNAC_HMI_DISPLAY_LAUNCH\r\n'
                       'NAC_HMI_DISPLAY_EXIT=127\r\nNAC_HMI_DISPLAY_LOG_END\r\n'
                       'NAC_HMI_DISPLAY_END\r\n')
        report = summarize_display(unrelated + display_log)
        self.assertTrue(report['hmi_display_probe_complete'])
        self.assertTrue(report['hmi_display_launch_observed'])
        self.assertEqual(report['hmi_display_exit_code'], 127)
        self.assertFalse(report['hmi_display_egl_surface_created'])
        self.assertFalse(report['hmi_display_frame_captured'])

    def test_cli_rejects_mixed_modes_without_touching_firmware(self):
        script = Path(__file__).resolve().parents[1]/'tools/run.py'
        result = subprocess.run([sys.executable,str(script),'--ui-probe','--hmi-probe'],
                                capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('Choose one diagnostic mode',result.stderr)

    def test_cli_rejects_unbounded_command_timeout_before_launching_qemu(self):
        script = Path(__file__).resolve().parents[1]/'tools/run.py'
        result = subprocess.run([sys.executable,str(script),'--command-timeout','301'],
                                capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('command-timeout must be between 1 and 300',result.stderr)

    def test_old_startup_checkpoint_does_not_claim_initialized_hmi(self):
        report = summarize('UIFwkMasterProcess::main Starting\nCUIFwkMasterProcess::run Creating Master\n')
        self.assertTrue(report['hmi_master_started'])
        for field in ['hmi_master_constructor_message_observed','hmi_master_event_loop_message_observed',
                      'hmi_master_initialization_message_observed','hmi_probe_complete','hmi_frame_verified']:
            self.assertFalse(report[field],field)

    def test_native_shared_memory_is_separate_from_constructor_and_frames(self):
        report = summarize('SettingsSharedMemory::ctor SHM shared.hmicommon.syshmi.ovip created with size 1428\n')
        self.assertTrue(report['hmi_settings_shared_memory_created'])
        self.assertFalse(report['hmi_master_constructor_message_observed'])
        self.assertFalse(report['rendered_frame_verified'])

    def test_bus_names_must_come_from_explicit_bus_inventory(self):
        text = 'log mentions string "org.genivi.NodeStateManager"\n'
        self.assertFalse(summarize(text)['native_nsm_on_bus'])
        self.assertFalse(summarize('\nNAC_HMI_BUS_NAMES\nstring "org.genivi.NodeStateManager"\n')['native_nsm_on_bus'])
        text += ('NAC_HMI_BUS_NAMES\r\nmethod return\r\n'
                 'string "org.genivi.NodeStateManager"\r\nstring "org.ovip.uifwk"\r\n'
                 'string "com.ovip.afw.ApplicationExecutionControl"\r\n'
                 'NAC_HMI_BUS_NAMES_END\r\n'
                 'NAC_HMI_STATE_END\r\n')
        report = summarize(text)
        self.assertTrue(report['native_nsm_on_bus'])
        self.assertTrue(report['native_hmi_on_bus'])
        self.assertTrue(report['native_framework_on_bus'])
        self.assertTrue(report['hmi_probe_complete'])
        self.assertFalse(report['hmi_frame_verified'])

    def test_bus_registration_does_not_imply_a_ping_reply_or_log_message(self):
        text = ('\nNAC_HMI_BUS_NAMES\nstring "org.ovip.uifwk"\nNAC_HMI_BUS_NAMES_END\n'
                'log mentions string "org.genivi.NodeStateManager"\n')
        report = summarize(text)
        self.assertTrue(report['native_hmi_on_bus'])
        self.assertFalse(report['native_nsm_on_bus'])
        self.assertFalse(report['hmi_bus_ping_verified'])
        self.assertFalse(report['hmi_master_initialization_message_observed'])
        self.assertTrue(summarize(text+'NAC_HMI_DBUS_PING_OK\n')['hmi_bus_ping_verified'])

    def test_diagnostic_end_does_not_imply_native_master_is_alive(self):
        report = summarize('\nNAC_HMI_STATE_END\n')
        self.assertTrue(report['hmi_probe_complete'])
        self.assertFalse(report['hmi_master_alive'])


if __name__ == '__main__':
    unittest.main()
