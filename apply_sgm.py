#!/usr/bin/env python3
"""SGM Keys Updater 2.1: add local automatic Tinfoil export to Lockpick_RCM.

Target: THZoria/Lockpick_RCMaster v2.0.1; GPLv2 derivative.
No keys or console secrets are packaged in this source distribution.
"""
from pathlib import Path
import argparse
import sys

EXPORT_FUNCTION = r'''/* SGM Keys Updater: local, staged Tinfoil export (never transmits keys). */
static void _sgm_export_tinfoil_keys(const char *key_data)
{
    const char *target = "sd:/switch/tinfoil/keys.txt";
    const char *temporary = "sd:/switch/tinfoil/keys.sgm.tmp";
    const char *backup = "sd:/switch/tinfoil/keys.sgm.bak";
    FILINFO info;
    FRESULT result;
    u32 length;
    bool had_previous;
    bool backup_ready = false;
    bool new_installed = false;

    if (!key_data || !strstr(key_data, "master_key_")) {
        EPRINTF("SGM: master keys missing; keys.txt preserved.");
        return;
    }
    length = (u32)strlen(key_data);
    if (length < 128 || length > SZ_32K) {
        EPRINTF("SGM: unexpected key file size; keys.txt preserved.");
        return;
    }
    result = f_mkdir("sd:/switch/tinfoil");
    if (result != FR_OK && result != FR_EXIST) {
        EPRINTF("SGM: cannot create Tinfoil folder.");
        return;
    }

    /* Create/verify a complete temporary file before touching the old one. */
    if (sd_save_to_file(key_data, length, temporary) ||
        f_stat(temporary, &info) != FR_OK || info.fsize != length) {
        EPRINTF("SGM: staging failed; old keys.txt preserved.");
        f_unlink(temporary);
        return;
    }

    had_previous = f_stat(target, &info) == FR_OK;
    if (had_previous) {
        /* Keep one backup. A failed backup removal must not touch target. */
        if (f_stat(backup, &info) == FR_OK && f_unlink(backup) != FR_OK) {
            EPRINTF("SGM: cannot rotate backup; old keys preserved.");
            f_unlink(temporary);
            return;
        }
        if (f_rename(target, backup) != FR_OK) {
            EPRINTF("SGM: cannot back up keys.txt; old keys preserved.");
            f_unlink(temporary);
            return;
        }
        backup_ready = true;
    }

    new_installed = f_rename(temporary, target) == FR_OK;
    if (new_installed && f_stat(target, &info) == FR_OK &&
        info.fsize == length) {
        gfx_printf("\nSGM: Tinfoil keys.txt updated!\n");
        gfx_printf("SGM: Path: /switch/tinfoil/keys.txt\n");
        return;
    }

    EPRINTF("SGM: final save failed; trying rollback.");
    if (new_installed)
        f_unlink(target);
    if (backup_ready && f_rename(backup, target) != FR_OK)
        EPRINTF("SGM: rollback failed; check keys.sgm.bak.");
    f_unlink(temporary);
}

'''

PROGRESS_HELPERS = r'''/* SGM V2.1 - stage-based progress; no synthetic byte percentage. */
static u32 _sgm_started_us = 0;
static void _sgm_stage(u32 finished, const char *description)
{
    char indicator[17];
    u32 blocks = finished * 16 / 7;
    u32 i;
    for (i = 0; i < 16; i++)
        indicator[i] = i < blocks ? '#' : '.';
    indicator[16] = 0;
    if (finished == 0)
        _sgm_started_us = get_tmr_us();
    gfx_printf("\nSGM [%s] phase %d/7: %s\n", indicator, finished, description);
    gfx_printf("SGM elapsed: %d seconds\n", (get_tmr_us() - _sgm_started_us) / 1000000);
}

'''

# Track real completed milestones, not a guessed completion percentage.
STAGE_PATCHES = (
    ('''    u32 start_whole_operation_time = get_tmr_us();''',
     '''    _sgm_stage(0, "Reading NAND - do not power off");
    u32 start_whole_operation_time = get_tmr_us();'''),
    ('''    minerva_periodic_training();

    if (emmc_storage.initialized && !emummc_storage_set_mmc_partition(EMMC_BOOT0)) {''',
     '''    _sgm_stage(1, "MMC initialized");
    minerva_periodic_training();

    if (emmc_storage.initialized && !emummc_storage_set_mmc_partition(EMMC_BOOT0)) {'''),
    ('''    TPRINTFARGS("%kMaster keys...  ", colors[(color_idx++) % 6]);''',
     '''    TPRINTFARGS("%kMaster keys...  ", colors[(color_idx++) % 6]);
    _sgm_stage(2, "Master keys derived");'''),
    ('''    TPRINTFARGS("%kBIS keys...     ", colors[(color_idx++) % 6]);''',
     '''    TPRINTFARGS("%kBIS keys...     ", colors[(color_idx++) % 6]);
    _sgm_stage(3, "BIS keys derived");'''),
    ('''    titlekey_buffer_t *titlekey_buffer = (titlekey_buffer_t *)TITLEKEY_BUF_ADR;''',
     '''    _sgm_stage(4, "Keys computed. Scanning tickets, may take 2+ min");
    titlekey_buffer_t *titlekey_buffer = (titlekey_buffer_t *)TITLEKEY_BUF_ADR;'''),
    ('''    end_time = get_tmr_us();
    gfx_printf("%kLockpick totally done in %d us\n", colors[(color_idx++) % 6], end_time - start_whole_operation_time);''',
     '''    _sgm_stage(5, "Tickets scanned");
    end_time = get_tmr_us();
    gfx_printf("%kLockpick totally done in %d us\n", colors[(color_idx++) % 6], end_time - start_whole_operation_time);'''),
    ('''        _save_keys_to_sd(keys, titlekey_buffer, is_dev, NULL, 0);''',
     '''        _sgm_stage(6, "Writing key files");
        _save_keys_to_sd(keys, titlekey_buffer, is_dev, NULL, 0);'''),
    ('''        _save_keys_to_sd(&prod_keys, titlekey_buffer, false, &new_keys, new_gen_mkr);''',
     '''        _sgm_stage(6, "Writing key files");
        _save_keys_to_sd(&prod_keys, titlekey_buffer, false, &new_keys, new_gen_mkr);'''),
    ('''        _save_keys_to_sd(&dev_keys, NULL, true, &new_keys_dev, new_gen_mkr);
    }
}''',
     '''        _save_keys_to_sd(&dev_keys, NULL, true, &new_keys_dev, new_gen_mkr);
    }
    _sgm_stage(7, "Operation ended - inspect result above");
}'''),
)

KEY_SAVE_BLOCK = '''    FILINFO fno;
    if (!sd_save_to_file(text_buffer, strlen(text_buffer), keyfile_path) && !f_stat(keyfile_path, &fno)) {
        gfx_printf("%kWrote %d bytes to %s\\n", colors[(color_idx++) % 6], (u32)fno.fsize, keyfile_path);
    } else {
        EPRINTF("Unable to save keys to SD.");
    }
'''

KEY_REPLACEMENT = '''    FILINFO fno;
    if (!sd_save_to_file(text_buffer, strlen(text_buffer), keyfile_path) && !f_stat(keyfile_path, &fno)) {
        gfx_printf("%kWrote %d bytes to %s\\n", colors[(color_idx++) % 6], (u32)fno.fsize, keyfile_path);
        if (!is_dev)
            _sgm_export_tinfoil_keys(text_buffer);
    } else {
        EPRINTF("Unable to save keys to SD.");
    }
'''

MAIN_BLOCK = '''\tminerva_change_freq(FREQ_800);

\twhile (true)
\t\ttui_do_menu(&menu_top);'''

MAIN_REPLACEMENT = '''\tminerva_change_freq(FREQ_800);

\t/* SGM: automatic local dump at startup; original menu remains available. */
\tgfx_printf("\\n=== SGM Keys Updater 2.1 ===\\n");
\tif (!h_cfg.emummc_force_disable && emu_cfg.enabled) {
\t\tgfx_printf("SGM: extracting configured emuMMC keys...\\n");
\t\tdump_emunand();
\t} else {
\t\tgfx_printf("SGM: extracting sysNAND keys...\\n");
\t\tdump_sysnand();
\t}
\tgfx_printf("\\nSGM: finished. Review any errors above.\\n");
\tgfx_printf("Press any button for the original Lockpick menu.\\n");
\tbtn_wait();

\twhile (true)
\t\ttui_do_menu(&menu_top);'''


def transform(keys_source: str, main_source: str) -> tuple[str, str]:
    """Patch both files in memory before writing either one."""
    if "_sgm_export_tinfoil_keys" in keys_source or "SGM Keys Updater 2.1" in main_source:
        if "_sgm_export_tinfoil_keys" in keys_source and "SGM Keys Updater 2.1" in main_source:
            return keys_source, main_source
        raise ValueError("Patching incomplete; do not apply over a partially patched source tree")
    if keys_source.count(KEY_SAVE_BLOCK) != 1:
        raise ValueError("Unexpected keys.c layout: source version incompatible")
    before_fn = "static void _save_keys_to_sd("
    if keys_source.count(before_fn) != 1:
        raise ValueError("Could not locate the key save function")
    if main_source.count(MAIN_BLOCK) != 1:
        raise ValueError("Unexpected main.c layout: source version incompatible")
    new_keys = keys_source.replace(before_fn, EXPORT_FUNCTION + PROGRESS_HELPERS + before_fn, 1)
    new_keys = new_keys.replace(KEY_SAVE_BLOCK, KEY_REPLACEMENT, 1)
    for original, patched in STAGE_PATCHES:
        if new_keys.count(original) != 1:
            raise ValueError("Progress anchor changed in upstream source: " + original[:65])
        new_keys = new_keys.replace(original, patched, 1)
    new_main = main_source.replace(MAIN_BLOCK, MAIN_REPLACEMENT, 1)
    return new_keys, new_main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Path to the unmodified Lockpick_RCM source repository")
    args = parser.parse_args()
    keys = args.source / "source/keys/keys.c"
    main_file = args.source / "source/main.c"
    if not keys.is_file() or not main_file.is_file():
        parser.error("source/keys/keys.c and source/main.c not found")
    keys_old, main_old = keys.read_text(), main_file.read_text()
    try:
        keys_new, main_new = transform(keys_old, main_old)
    except ValueError as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    if keys_new == keys_old and main_new == main_old:
        print("Already patched. No changes made.")
        return 0
    keys.write_text(keys_new)
    main_file.write_text(main_new)
    print("SGM Keys Updater 2.1 patch applied to", args.source)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
