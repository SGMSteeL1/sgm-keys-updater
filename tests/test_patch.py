import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_sgm import KEY_SAVE_BLOCK, MAIN_BLOCK, STAGE_PATCHES, transform

class PatchTest(unittest.TestCase):
    def setUp(self):
        self.keys = 'header\nstatic void _save_keys_to_sd(whatever) {\n' + KEY_SAVE_BLOCK + '\n}\n' + '\n'.join(original for original, _ in STAGE_PATCHES)
        self.main = 'header\n' + MAIN_BLOCK + '\nfooter\n'

    def test_success_and_idempotent(self):
        k, m = transform(self.keys, self.main)
        self.assertIn('_sgm_export_tinfoil_keys(text_buffer)', k)
        self.assertIn('f_rename(temporary, target)', k)
        self.assertIn('SGM Keys Updater 2.1', m)
        self.assertIn('dump_emunand()', m)
        self.assertIn('dump_sysnand()', m)
        self.assertEqual((k, m), transform(k, m))

    def test_fail_without_touching_source(self):
        with self.assertRaises(ValueError):
            transform(self.keys.replace('FILINFO fno;', 'FILINFO wrong;'), self.main)
        with self.assertRaises(ValueError):
            transform(self.keys, 'bad main layout')

    def test_no_embedded_crypto_secrets(self):
        k, m = transform(self.keys, self.main)
        self.assertIn('master_key_', k)
        self.assertNotIn('https://', k + m)
        self.assertNotIn('curl', k + m)

if __name__ == '__main__':
    unittest.main()
