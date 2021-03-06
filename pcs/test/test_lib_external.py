import logging
from subprocess import DEVNULL
from unittest import mock, TestCase

from pcs.test.tools.assertions import (
    assert_raise_library_error,
    assert_report_item_list_equal,
)
from pcs.test.tools.custom_mock import MockLibraryReportProcessor
from pcs.test.tools.misc import outdent

from pcs import settings
from pcs.common import report_codes
from pcs.lib.errors import ReportItemSeverity as severity

import pcs.lib.external as lib


_chkconfig = settings.chkconfig_binary
_service = settings.service_binary
_systemctl = settings.systemctl_binary


@mock.patch("subprocess.Popen", autospec=True)
class CommandRunnerTest(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()

    def assert_popen_called_with(self, mock_popen, args, kwargs):
        self.assertEqual(mock_popen.call_count, 1)
        real_args, real_kwargs = mock_popen.call_args
        filtered_kwargs = dict([
            (name, value) for name, value in real_kwargs.items()
            if name in kwargs
        ])
        self.assertEqual(real_args, (args,))
        self.assertEqual(filtered_kwargs, kwargs)

    def test_basic(self, mock_popen):
        expected_stdout = "expected stdout"
        expected_stderr = "expected stderr"
        expected_retval = 123
        command = ["a_command"]
        command_str = "a_command"
        mock_process = mock.MagicMock(spec_set=["communicate", "returncode"])
        mock_process.communicate.return_value = (
            expected_stdout, expected_stderr
        )
        mock_process.returncode = expected_retval
        mock_popen.return_value = mock_process

        runner = lib.CommandRunner(self.mock_logger, self.mock_reporter)
        real_stdout, real_stderr, real_retval = runner.run(command)

        self.assertEqual(real_stdout, expected_stdout)
        self.assertEqual(real_stderr, expected_stderr)
        self.assertEqual(real_retval, expected_retval)
        mock_process.communicate.assert_called_once_with(None)
        self.assert_popen_called_with(
            mock_popen,
            command,
            {"env": {}, "stdin": DEVNULL,}
        )
        logger_calls = [
            mock.call("Running: {0}\nEnvironment:".format(command_str)),
            mock.call(
                outdent(
                    """\
                    Finished running: {0}
                    Return value: {1}
                    --Debug Stdout Start--
                    {2}
                    --Debug Stdout End--
                    --Debug Stderr Start--
                    {3}
                    --Debug Stderr End--"""
                ).format(
                    command_str,
                    expected_retval,
                    expected_stdout,
                    expected_stderr,
                )
            )
        ]
        self.assertEqual(self.mock_logger.debug.call_count, len(logger_calls))
        self.mock_logger.debug.assert_has_calls(logger_calls)
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_STARTED,
                    {
                        "command": command_str,
                        "stdin": None,
                        "environment": dict(),
                    }
                ),
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_FINISHED,
                    {
                        "command": command_str,
                        "return_value": expected_retval,
                        "stdout": expected_stdout,
                        "stderr": expected_stderr,
                    }
                )
            ]
        )

    def test_env(self, mock_popen):
        expected_stdout = "expected output"
        expected_stderr = "expected stderr"
        expected_retval = 123
        command = ["a_command"]
        command_str = "a_command"
        mock_process = mock.MagicMock(spec_set=["communicate", "returncode"])
        mock_process.communicate.return_value = (
            expected_stdout, expected_stderr
        )
        mock_process.returncode = expected_retval
        mock_popen.return_value = mock_process

        global_env = {"a": "a", "b": "b"}
        runner = lib.CommandRunner(
            self.mock_logger,
            self.mock_reporter,
            global_env.copy()
        )
        #{C} is for check that no python template conflict appear
        real_stdout, real_stderr, real_retval = runner.run(
            command,
            env_extend={"b": "B", "c": "{C}"}
        )
        #check that env_exted did not affect initial env of runner
        self.assertEqual(runner._env_vars, global_env)

        self.assertEqual(real_stdout, expected_stdout)
        self.assertEqual(real_stderr, expected_stderr)
        self.assertEqual(real_retval, expected_retval)
        mock_process.communicate.assert_called_once_with(None)
        self.assert_popen_called_with(
            mock_popen,
            command,
            {"env": {"a": "a", "b": "B", "c": "{C}"}, "stdin": DEVNULL,}
        )
        logger_calls = [
            mock.call(
                outdent(
                    """\
                    Running: {0}
                    Environment:
                      a=a
                      b=B
                      c={1}"""
                ).format(command_str, "{C}")
            ),
            mock.call(
                outdent(
                    """\
                    Finished running: {0}
                    Return value: {1}
                    --Debug Stdout Start--
                    {2}
                    --Debug Stdout End--
                    --Debug Stderr Start--
                    {3}
                    --Debug Stderr End--"""
                ).format(
                    command_str,
                    expected_retval,
                    expected_stdout,
                    expected_stderr,
                )
            )
        ]
        self.assertEqual(self.mock_logger.debug.call_count, len(logger_calls))
        self.mock_logger.debug.assert_has_calls(logger_calls)
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_STARTED,
                    {
                        "command": command_str,
                        "stdin": None,
                        "environment": {"a": "a", "b": "B", "c": "{C}"},
                    }
                ),
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_FINISHED,
                    {
                        "command": command_str,
                        "return_value": expected_retval,
                        "stdout": expected_stdout,
                        "stderr": expected_stderr,
                    }
                )
            ]
        )

    def test_stdin(self, mock_popen):
        expected_stdout = "expected output"
        expected_stderr = "expected stderr"
        expected_retval = 123
        command = ["a_command"]
        command_str = "a_command"
        stdin = "stdin string"
        mock_process = mock.MagicMock(spec_set=["communicate", "returncode"])
        mock_process.communicate.return_value = (
            expected_stdout, expected_stderr
        )
        mock_process.returncode = expected_retval
        mock_popen.return_value = mock_process

        runner = lib.CommandRunner(self.mock_logger, self.mock_reporter)
        real_stdout, real_stderr, real_retval = runner.run(
            command, stdin_string=stdin
        )

        self.assertEqual(real_stdout, expected_stdout)
        self.assertEqual(real_stderr, expected_stderr)
        self.assertEqual(real_retval, expected_retval)
        mock_process.communicate.assert_called_once_with(stdin)
        self.assert_popen_called_with(
            mock_popen,
            command,
            {"env": {}, "stdin": -1}
        )
        logger_calls = [
            mock.call(
                outdent(
                    """\
                    Running: {0}
                    Environment:
                    --Debug Input Start--
                    {1}
                    --Debug Input End--"""
                ).format(command_str, stdin)
            ),
            mock.call(
                outdent(
                    """\
                    Finished running: {0}
                    Return value: {1}
                    --Debug Stdout Start--
                    {2}
                    --Debug Stdout End--
                    --Debug Stderr Start--
                    {3}
                    --Debug Stderr End--"""
                ).format(
                    command_str,
                    expected_retval,
                    expected_stdout,
                    expected_stderr,
            ))
        ]
        self.assertEqual(self.mock_logger.debug.call_count, len(logger_calls))
        self.mock_logger.debug.assert_has_calls(logger_calls)
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_STARTED,
                    {
                        "command": command_str,
                        "stdin": stdin,
                        "environment": dict(),
                    }
                ),
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_FINISHED,
                    {
                        "command": command_str,
                        "return_value": expected_retval,
                        "stdout": expected_stdout,
                        "stderr": expected_stderr,
                    }
                )
            ]
        )

    def test_popen_error(self, mock_popen):
        expected_error = "expected error"
        command = ["a_command"]
        command_str = "a_command"
        mock_process = mock.MagicMock(spec_set=["communicate", "returncode"])
        exception = OSError()
        exception.strerror = expected_error
        mock_popen.side_effect = exception

        runner = lib.CommandRunner(self.mock_logger, self.mock_reporter)
        assert_raise_library_error(
            lambda: runner.run(command),
            (
                severity.ERROR,
                report_codes.RUN_EXTERNAL_PROCESS_ERROR,
                {
                    "command": command_str,
                    "reason": expected_error,
                }
            )
        )

        mock_process.communicate.assert_not_called()
        self.assert_popen_called_with(
            mock_popen,
            command,
            {"env": {}, "stdin": DEVNULL,}
        )
        logger_calls = [
            mock.call("Running: {0}\nEnvironment:".format(command_str)),
        ]
        self.assertEqual(self.mock_logger.debug.call_count, len(logger_calls))
        self.mock_logger.debug.assert_has_calls(logger_calls)
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_STARTED,
                    {
                        "command": command_str,
                        "stdin": None,
                        "environment": dict(),
                    }
                )
            ]
        )

    def test_communicate_error(self, mock_popen):
        expected_error = "expected error"
        command = ["a_command"]
        command_str = "a_command"
        mock_process = mock.MagicMock(spec_set=["communicate", "returncode"])
        exception = OSError()
        exception.strerror = expected_error
        mock_process.communicate.side_effect = exception
        mock_popen.return_value = mock_process

        runner = lib.CommandRunner(self.mock_logger, self.mock_reporter)
        assert_raise_library_error(
            lambda: runner.run(command),
            (
                severity.ERROR,
                report_codes.RUN_EXTERNAL_PROCESS_ERROR,
                {
                    "command": command_str,
                    "reason": expected_error,
                }
            )
        )

        mock_process.communicate.assert_called_once_with(None)
        self.assert_popen_called_with(
            mock_popen,
            command,
            {"env": {}, "stdin": DEVNULL,}
        )
        logger_calls = [
            mock.call("Running: {0}\nEnvironment:".format(command_str)),
        ]
        self.assertEqual(self.mock_logger.debug.call_count, len(logger_calls))
        self.mock_logger.debug.assert_has_calls(logger_calls)
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.DEBUG,
                    report_codes.RUN_EXTERNAL_PROCESS_STARTED,
                    {
                        "command": command_str,
                        "stdin": None,
                        "environment": dict(),
                    }
                )
            ]
        )


@mock.patch("pcs.lib.external.is_systemctl")
@mock.patch("pcs.lib.external.is_service_installed")
class DisableServiceTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)
        self.service = "service_name"

    def test_systemctl(self, mock_is_installed, mock_systemctl):
        mock_is_installed.return_value = True
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Removed symlink", 0)
        lib.disable_service(self.mock_runner, self.service)
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, None
        )
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "disable", self.service + ".service"]
        )

    def test_systemctl_failed(self, mock_is_installed, mock_systemctl):
        mock_is_installed.return_value = True
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Failed", 1)
        self.assertRaises(
            lib.DisableServiceError,
            lambda: lib.disable_service(self.mock_runner, self.service)
        )
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, None
        )
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "disable", self.service + ".service"]
        )

    def test_not_systemctl(self, mock_is_installed, mock_systemctl):
        mock_is_installed.return_value = True
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "", 0)
        lib.disable_service(self.mock_runner, self.service)
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, None
        )
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service, "off"]
        )

    def test_not_systemctl_failed(self, mock_is_installed, mock_systemctl):
        mock_is_installed.return_value = True
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "error", 1)
        self.assertRaises(
            lib.DisableServiceError,
            lambda: lib.disable_service(self.mock_runner, self.service)
        )
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, None
        )
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service, "off"]
        )

    def test_systemctl_not_installed(
            self, mock_is_installed, mock_systemctl
    ):
        mock_is_installed.return_value = False
        mock_systemctl.return_value = True
        lib.disable_service(self.mock_runner, self.service)
        self.assertEqual(self.mock_runner.run.call_count, 0)
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, None
        )

    def test_not_systemctl_not_installed(
            self, mock_is_installed, mock_systemctl
    ):
        mock_is_installed.return_value = False
        mock_systemctl.return_value = False
        lib.disable_service(self.mock_runner, self.service)
        self.assertEqual(self.mock_runner.run.call_count, 0)
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, None
        )

    def test_instance_systemctl(self, mock_is_installed, mock_systemctl):
        instance = "test"
        mock_is_installed.return_value = True
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Removed symlink", 0)
        lib.disable_service(self.mock_runner, self.service, instance=instance)
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, instance
        )
        self.mock_runner.run.assert_called_once_with([
            _systemctl,
            "disable",
            "{0}@{1}.service".format(self.service, "test")
        ])

    def test_instance_not_systemctl(self, mock_is_installed, mock_systemctl):
        instance = "test"
        mock_is_installed.return_value = True
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "", 0)
        lib.disable_service(self.mock_runner, self.service, instance=instance)
        mock_is_installed.assert_called_once_with(
            self.mock_runner, self.service, instance
        )
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service, "off"]
        )

@mock.patch("pcs.lib.external.is_systemctl")
class EnableServiceTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)
        self.service = "service_name"

    def test_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Created symlink", 0)
        lib.enable_service(self.mock_runner, self.service)
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "enable", self.service + ".service"]
        )

    def test_systemctl_failed(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Failed", 1)
        self.assertRaises(
            lib.EnableServiceError,
            lambda: lib.enable_service(self.mock_runner, self.service)
        )
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "enable", self.service + ".service"]
        )

    def test_not_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "", 0)
        lib.enable_service(self.mock_runner, self.service)
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service, "on"]
        )

    def test_not_systemctl_failed(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "error", 1)
        self.assertRaises(
            lib.EnableServiceError,
            lambda: lib.enable_service(self.mock_runner, self.service)
        )
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service, "on"]
        )

    def test_instance_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Created symlink", 0)
        lib.enable_service(self.mock_runner, self.service, instance="test")
        self.mock_runner.run.assert_called_once_with([
            _systemctl,
            "enable",
            "{0}@{1}.service".format(self.service, "test")
        ])

    def test_instance_not_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "", 0)
        lib.enable_service(self.mock_runner, self.service, instance="test")
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service, "on"]
        )


@mock.patch("pcs.lib.external.is_systemctl")
class StartServiceTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)
        self.service = "service_name"

    def test_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "", 0)
        lib.start_service(self.mock_runner, self.service)
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "start", self.service + ".service"]
        )

    def test_systemctl_failed(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Failed", 1)
        self.assertRaises(
            lib.StartServiceError,
            lambda: lib.start_service(self.mock_runner, self.service)
        )
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "start", self.service + ".service"]
        )

    def test_not_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("Starting...", "", 0)
        lib.start_service(self.mock_runner, self.service)
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "start"]
        )

    def test_not_systemctl_failed(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "unrecognized", 1)
        self.assertRaises(
            lib.StartServiceError,
            lambda: lib.start_service(self.mock_runner, self.service)
        )
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "start"]
        )

    def test_instance_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "", 0)
        lib.start_service(self.mock_runner, self.service, instance="test")
        self.mock_runner.run.assert_called_once_with([
            _systemctl, "start", "{0}@{1}.service".format(self.service, "test")
        ])

    def test_instance_not_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("Starting...", "", 0)
        lib.start_service(self.mock_runner, self.service, instance="test")
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "start"]
        )


@mock.patch("pcs.lib.external.is_systemctl")
class StopServiceTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)
        self.service = "service_name"

    def test_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "", 0)
        lib.stop_service(self.mock_runner, self.service)
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "stop", self.service + ".service"]
        )

    def test_systemctl_failed(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "Failed", 1)
        self.assertRaises(
            lib.StopServiceError,
            lambda: lib.stop_service(self.mock_runner, self.service)
        )
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "stop", self.service + ".service"]
        )

    def test_not_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("Stopping...", "", 0)
        lib.stop_service(self.mock_runner, self.service)
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "stop"]
        )

    def test_not_systemctl_failed(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "unrecognized", 1)
        self.assertRaises(
            lib.StopServiceError,
            lambda: lib.stop_service(self.mock_runner, self.service)
        )
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "stop"]
        )

    def test_instance_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", "", 0)
        lib.stop_service(self.mock_runner, self.service, instance="test")
        self.mock_runner.run.assert_called_once_with([
            _systemctl, "stop", "{0}@{1}.service".format(self.service, "test")
        ])

    def test_instance_not_systemctl(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("Stopping...", "", 0)
        lib.stop_service(self.mock_runner, self.service, instance="test")
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "stop"]
        )


class KillServicesTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)
        self.services = ["service1", "service2"]

    def test_success(self):
        self.mock_runner.run.return_value = ("", "", 0)
        lib.kill_services(self.mock_runner, self.services)
        self.mock_runner.run.assert_called_once_with(
            ["killall", "--quiet", "--signal", "9", "--"] + self.services
        )

    def test_failed(self):
        self.mock_runner.run.return_value = ("", "error", 1)
        self.assertRaises(
            lib.KillServicesError,
            lambda: lib.kill_services(self.mock_runner, self.services)
        )
        self.mock_runner.run.assert_called_once_with(
            ["killall", "--quiet", "--signal", "9", "--"] + self.services
        )

    def test_service_not_running(self):
        self.mock_runner.run.return_value = ("", "", 1)
        lib.kill_services(self.mock_runner, self.services)
        self.mock_runner.run.assert_called_once_with(
            ["killall", "--quiet", "--signal", "9", "--"] + self.services
        )


@mock.patch("pcs.lib.external.is_systemctl")
class IsServiceEnabledTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)
        self.service = "service_name"

    def test_systemctl_enabled(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("enabled\n", "", 0)
        self.assertTrue(lib.is_service_enabled(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "is-enabled", self.service + ".service"]
        )

    def test_systemctl_disabled(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("disabled\n", "", 2)
        self.assertFalse(lib.is_service_enabled(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "is-enabled", self.service + ".service"]
        )

    def test_not_systemctl_enabled(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "", 0)
        self.assertTrue(lib.is_service_enabled(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service]
        )

    def test_not_systemctl_disabled(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("", "", 3)
        self.assertFalse(lib.is_service_enabled(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_chkconfig, self.service]
        )


@mock.patch("pcs.lib.external.is_systemctl")
class IsServiceRunningTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)
        self.service = "service_name"

    def test_systemctl_running(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("active", "", 0)
        self.assertTrue(lib.is_service_running(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "is-active", self.service + ".service"]
        )

    def test_systemctl_not_running(self, mock_systemctl):
        mock_systemctl.return_value = True
        self.mock_runner.run.return_value = ("inactive", "", 2)
        self.assertFalse(lib.is_service_running(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "is-active", self.service + ".service"]
        )

    def test_not_systemctl_running(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("is running", "", 0)
        self.assertTrue(lib.is_service_running(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "status"]
        )

    def test_not_systemctl_not_running(self, mock_systemctl):
        mock_systemctl.return_value = False
        self.mock_runner.run.return_value = ("is stopped", "", 3)
        self.assertFalse(lib.is_service_running(self.mock_runner, self.service))
        self.mock_runner.run.assert_called_once_with(
            [_service, self.service, "status"]
        )


@mock.patch("pcs.lib.external.is_systemctl")
@mock.patch("pcs.lib.external.get_systemd_services")
@mock.patch("pcs.lib.external.get_non_systemd_services")
class IsServiceInstalledTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)

    def test_installed_systemd(
        self, mock_non_systemd, mock_systemd, mock_is_systemctl
    ):
        mock_is_systemctl.return_value = True
        mock_systemd.return_value = ["service1", "service2"]
        mock_non_systemd.return_value = []
        self.assertTrue(lib.is_service_installed(self.mock_runner, "service2"))
        self.assertEqual(mock_is_systemctl.call_count, 1)
        mock_systemd.assert_called_once_with(self.mock_runner)
        self.assertEqual(mock_non_systemd.call_count, 0)

    def test_not_installed_systemd(
            self, mock_non_systemd, mock_systemd, mock_is_systemctl
    ):
        mock_is_systemctl.return_value = True
        mock_systemd.return_value = ["service1", "service2"]
        mock_non_systemd.return_value = []
        self.assertFalse(lib.is_service_installed(self.mock_runner, "service3"))
        self.assertEqual(mock_is_systemctl.call_count, 1)
        mock_systemd.assert_called_once_with(self.mock_runner)
        self.assertEqual(mock_non_systemd.call_count, 0)

    def test_installed_not_systemd(
            self, mock_non_systemd, mock_systemd, mock_is_systemctl
    ):
        mock_is_systemctl.return_value = False
        mock_systemd.return_value = []
        mock_non_systemd.return_value = ["service1", "service2"]
        self.assertTrue(lib.is_service_installed(self.mock_runner, "service2"))
        self.assertEqual(mock_is_systemctl.call_count, 1)
        mock_non_systemd.assert_called_once_with(self.mock_runner)
        self.assertEqual(mock_systemd.call_count, 0)

    def test_not_installed_not_systemd(
            self, mock_non_systemd, mock_systemd, mock_is_systemctl
    ):
        mock_is_systemctl.return_value = False

        mock_systemd.return_value = []
        mock_non_systemd.return_value = ["service1", "service2"]
        self.assertFalse(lib.is_service_installed(self.mock_runner, "service3"))
        self.assertEqual(mock_is_systemctl.call_count, 1)
        mock_non_systemd.assert_called_once_with(self.mock_runner)
        self.assertEqual(mock_systemd.call_count, 0)

    def test_installed_systemd_instance(
        self, mock_non_systemd, mock_systemd, mock_is_systemctl
    ):
        mock_is_systemctl.return_value = True
        mock_systemd.return_value = ["service1", "service2@"]
        mock_non_systemd.return_value = []
        self.assertTrue(
            lib.is_service_installed(self.mock_runner, "service2", "instance")
        )
        self.assertEqual(mock_is_systemctl.call_count, 1)
        mock_systemd.assert_called_once_with(self.mock_runner)
        self.assertEqual(mock_non_systemd.call_count, 0)

    def test_not_installed_systemd_instance(
        self, mock_non_systemd, mock_systemd, mock_is_systemctl
    ):
        mock_is_systemctl.return_value = True
        mock_systemd.return_value = ["service1", "service2"]
        mock_non_systemd.return_value = []
        self.assertFalse(
            lib.is_service_installed(self.mock_runner, "service2", "instance")
        )
        self.assertEqual(mock_is_systemctl.call_count, 1)
        mock_systemd.assert_called_once_with(self.mock_runner)
        self.assertEqual(mock_non_systemd.call_count, 0)

    def test_installed_not_systemd_instance(
        self, mock_non_systemd, mock_systemd, mock_is_systemctl
    ):
        mock_is_systemctl.return_value = False
        mock_systemd.return_value = []
        mock_non_systemd.return_value = ["service1", "service2"]
        self.assertTrue(
            lib.is_service_installed(self.mock_runner, "service2", "instance")
        )
        self.assertEqual(mock_is_systemctl.call_count, 1)
        mock_non_systemd.assert_called_once_with(self.mock_runner)
        self.assertEqual(mock_systemd.call_count, 0)


@mock.patch("pcs.lib.external.is_systemctl")
class GetSystemdServicesTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)

    def test_success(self, mock_is_systemctl):
        mock_is_systemctl.return_value = True
        self.mock_runner.run.return_value = (outdent(
            """\
            pcsd.service                                disabled
            sbd.service                                 enabled
            pacemaker.service                           enabled

            3 unit files listed.
            """
        ), "", 0)
        self.assertEqual(
            lib.get_systemd_services(self.mock_runner),
            ["pcsd", "sbd", "pacemaker"]
        )
        self.assertEqual(mock_is_systemctl.call_count, 1)
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "list-unit-files", "--full"]
        )

    def test_failed(self, mock_is_systemctl):
        mock_is_systemctl.return_value = True
        self.mock_runner.run.return_value = ("stdout", "failed", 1)
        self.assertEqual(lib.get_systemd_services(self.mock_runner), [])
        self.assertEqual(mock_is_systemctl.call_count, 1)
        self.mock_runner.run.assert_called_once_with(
            [_systemctl, "list-unit-files", "--full"]
        )

    def test_not_systemd(self, mock_is_systemctl):
        mock_is_systemctl.return_value = False
        self.assertEqual(lib.get_systemd_services(self.mock_runner), [])
        mock_is_systemctl.assert_called_once_with()
        self.mock_runner.assert_not_called()


@mock.patch("pcs.lib.external.is_systemctl")
class GetNonSystemdServicesTest(TestCase):
    def setUp(self):
        self.mock_runner = mock.MagicMock(spec_set=lib.CommandRunner)

    def test_success(self, mock_is_systemctl):
        mock_is_systemctl.return_value = False
        self.mock_runner.run.return_value = (outdent(
            """\
            pcsd           	0:off	1:off	2:on	3:on	4:on	5:on	6:off
            sbd            	0:off	1:on	2:on	3:on	4:on	5:on	6:off
            pacemaker      	0:off	1:off	2:off	3:off	4:off	5:off	6:off
            """
        ), "", 0)
        self.assertEqual(
            lib.get_non_systemd_services(self.mock_runner),
            ["pcsd", "sbd", "pacemaker"]
        )
        self.assertEqual(mock_is_systemctl.call_count, 1)
        self.mock_runner.run.assert_called_once_with([_chkconfig])

    def test_failed(self, mock_is_systemctl):
        mock_is_systemctl.return_value = False
        self.mock_runner.run.return_value = ("stdout", "failed", 1)
        self.assertEqual(lib.get_non_systemd_services(self.mock_runner), [])
        self.assertEqual(mock_is_systemctl.call_count, 1)
        self.mock_runner.run.assert_called_once_with([_chkconfig])

    def test_systemd(self, mock_is_systemctl):
        mock_is_systemctl.return_value = True
        self.mock_runner.run.return_value = ("", 0)
        self.assertEqual(lib.get_non_systemd_services(self.mock_runner), [])
        self.assertEqual(mock_is_systemctl.call_count, 1)
        self.assertEqual(self.mock_runner.call_count, 0)

@mock.patch("pcs.lib.external.is_systemctl")
class EnsureIsSystemctlTest(TestCase):
    def test_systemd(self, mock_is_systemctl):
        mock_is_systemctl.return_value = True
        lib.ensure_is_systemd()

    def test_not_systemd(self, mock_is_systemctl):
        mock_is_systemctl.return_value = False
        assert_raise_library_error(
            lib.ensure_is_systemd,
            (
                severity.ERROR,
                report_codes.UNSUPPORTED_OPERATION_ON_NON_SYSTEMD_SYSTEMS,
                {}
            )
        )


class IsProxySetTest(TestCase):
    def test_without_proxy(self):
        self.assertFalse(lib.is_proxy_set({
            "var1": "value",
            "var2": "val",
        }))

    def test_multiple(self):
        self.assertTrue(lib.is_proxy_set({
            "var1": "val",
            "https_proxy": "test.proxy",
            "var2": "val",
            "all_proxy": "test2.proxy",
            "var3": "val",
        }))

    def test_empty_string(self):
        self.assertFalse(lib.is_proxy_set({
            "all_proxy": "",
        }))

    def test_http_proxy(self):
        self.assertFalse(lib.is_proxy_set({
            "http_proxy": "test.proxy",
        }))

    def test_HTTP_PROXY(self):
        self.assertFalse(lib.is_proxy_set({
            "HTTP_PROXY": "test.proxy",
        }))

    def test_https_proxy(self):
        self.assertTrue(lib.is_proxy_set({
            "https_proxy": "test.proxy",
        }))

    def test_HTTPS_PROXY(self):
        self.assertTrue(lib.is_proxy_set({
            "HTTPS_PROXY": "test.proxy",
        }))

    def test_all_proxy(self):
        self.assertTrue(lib.is_proxy_set({
            "all_proxy": "test.proxy",
        }))

    def test_ALL_PROXY(self):
        self.assertTrue(lib.is_proxy_set({
            "ALL_PROXY": "test.proxy",
        }))

    def test_no_proxy(self):
        self.assertTrue(lib.is_proxy_set({
            "no_proxy": "*",
            "all_proxy": "test.proxy",
        }))
