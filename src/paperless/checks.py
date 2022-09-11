import os
import shutil
import stat

from django.conf import settings
from django.core.checks import Error
from django.core.checks import register
from django.core.checks import Warning

exists_message = "{} is set but doesn't exist."
exists_hint = "Create a directory at {}"
writeable_message = "{} is not writeable"
writeable_hint = (
    "Set the permissions of {} to be writeable by the user running the "
    "Paperless services"
)


def path_check(var, directory):
    messages = []
    if directory:
        if not os.path.isdir(directory):
            messages.append(
                Error(exists_message.format(var), exists_hint.format(directory)),
            )
        else:
            test_file = os.path.join(
                directory,
                f"__paperless_write_test_{os.getpid()}__",
            )
            try:
                with open(test_file, "w"):
                    pass
            except PermissionError:
                messages.append(
                    Error(
                        writeable_message.format(var),
                        writeable_hint.format(
                            f"\n{stat.filemode(os.stat(directory).st_mode)} "
                            f"{directory}\n",
                        ),
                    ),
                )
            finally:
                if os.path.isfile(test_file):
                    os.remove(test_file)

    return messages


@register()
def paths_check(app_configs, **kwargs):
    """
    Check the various paths for existence, readability and writeability
    """

    return (
        path_check("PAPERLESS_DATA_DIR", settings.DATA_DIR)
        + path_check("PAPERLESS_TRASH_DIR", settings.TRASH_DIR)
        + path_check("PAPERLESS_MEDIA_ROOT", settings.MEDIA_ROOT)
        + path_check("PAPERLESS_CONSUMPTION_DIR", settings.CONSUMPTION_DIR)
    )


@register()
def binaries_check(app_configs, **kwargs):
    """
    Paperless requires the existence of a few binaries, so we do some checks
    for those here.
    """

    error = "Paperless can't find {}. Without it, consumption is impossible."
    hint = "Either it's not in your ${PATH} or it's not installed."

    binaries = (settings.CONVERT_BINARY, "tesseract")

    check_messages = []
    for binary in binaries:
        if shutil.which(binary) is None:
            check_messages.append(Warning(error.format(binary), hint))

    return check_messages


@register()
def debug_mode_check(app_configs, **kwargs):
    if settings.DEBUG:
        return [
            Warning(
                "DEBUG mode is enabled. Disable Debug mode. This is a serious "
                "security issue, since it puts security overides in place which "
                "are meant to be only used during development. This "
                "also means that paperless will tell anyone various "
                "debugging information when something goes wrong.",
            ),
        ]
    else:
        return []


@register()
def settings_values_check(app_configs, **kwargs):
    """
    Validates at least some of the user provided settings
    """

    def _ocrmypdf_settings_check():
        """
        Validates some of the arguments which will be provided to ocrmypdf
        against the valid options.  Use "ocrmypdf --help" to see the valid
        inputs
        """
        msgs = []
        if settings.OCR_OUTPUT_TYPE not in {
            "pdfa",
            "pdf",
            "pdfa-1",
            "pdfa-2",
            "pdfa-3",
        }:
            msgs.append(
                Error(f'OCR output type "{settings.OCR_OUTPUT_TYPE}" is not valid'),
            )

        if settings.OCR_MODE not in {"force", "skip", "redo_ocr"}:
            msgs.append(Error(f'OCR output mode "{settings.OCR_MODE}" is not valid'))

        if settings.OCR_CLEAN not in {"clean", "clean_final"}:
            msgs.append(Error(f'OCR clean mode "{settings.OCR_CLEAN}" is not valid'))
        return msgs

    def _timezone_validate():
        """
        Validates the user provided timezone is a valid timezone
        """
        try:
            import zoneinfo
        except ImportError:  # pragma: nocover
            import backports.zoneinfo as zoneinfo
        msgs = []
        if settings.TIME_ZONE not in zoneinfo.available_timezones():
            msgs.append(
                Error(f'Timezone "{settings.TIME_ZONE}" is not a valid timezone'),
            )
        return msgs

    return _ocrmypdf_settings_check() + _timezone_validate()
