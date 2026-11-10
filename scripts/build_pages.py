"""Build only public app assets for GitHub Pages (never server data or secrets)."""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def build(destination=None):
    output = Path(destination) if destination else ROOT / 'dist'
    output.mkdir(parents=True, exist_ok=True)
    for name in ['index.html', 'app.js', 'pages.js', 'styles.css', 'phone.css',
                 'logo.svg', 'manifest.json', 'sw.js']:
        shutil.copyfile(ROOT / 'public' / name, output / name)
    shutil.copytree(ROOT / 'public/locales', output / 'locales', dirs_exist_ok=True)
    content = {name: json.loads((ROOT / f'src/data/{name}.json').read_text(encoding='utf-8'))
               for name in ['universities', 'lessons', 'visas', 'updates', 'processes']}
    (output / 'content.json').write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    index = (output / 'index.html').read_text(encoding='utf-8')
    index = index.replace('  <script src="app.js', '  <script src="pages.js" defer></script>\n  <script src="app.js')
    (output / 'index.html').write_text(index, encoding='utf-8')
    worker = (output / 'sw.js').read_text(encoding='utf-8')
    worker = worker.replace("'api/content'", "'content.json', 'pages.js'")
    (output / 'sw.js').write_text(worker, encoding='utf-8')
    (output / '.nojekyll').touch()
    return output


if __name__ == '__main__':
    print(f'GitHub Pages app built in {build()}')
