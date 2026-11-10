import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_pages import build


class PagesBuild(unittest.TestCase):
    def test_public_build_works_under_repository_path(self):
        with tempfile.TemporaryDirectory() as directory:
            output = build(directory)
            index = (output / 'index.html').read_text(encoding='utf-8')
            self.assertIn('src="pages.js"', index)
            self.assertNotIn('src="/', index)
            self.assertNotIn('href="/', index)
            self.assertEqual(len(json.loads((output / 'content.json').read_text(encoding='utf-8'))['lessons']), 12)
            self.assertEqual(json.loads((output / 'manifest.json').read_text())['start_url'], './')
            worker = (output / 'sw.js').read_text()
            self.assertIn("'content.json', 'pages.js'", worker)
            self.assertNotIn('api/content', worker)
            self.assertEqual({p.name for p in Path(directory).iterdir()}, {
                'index.html', 'app.js', 'pages.js', 'styles.css', 'phone.css',
                'logo.svg', 'manifest.json', 'sw.js', 'locales', 'content.json', '.nojekyll'})
