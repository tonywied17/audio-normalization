import sys
import json
import importlib
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import builtins


def reload_conf():
    if 'core.config' in sys.modules:
        del sys.modules['core.config']
    import core.config as conf
    importlib.reload(conf)
    return conf


def test_write_default_config_writes_file(tmp_path):
    conf = reload_conf()
    p = tmp_path / 'cfg.json'
    conf._write_default_config(str(p))
    assert p.exists()
    data = json.loads(p.read_text(encoding='utf-8'))
    assert data.get('VERSION') == conf.VERSION
    assert 'NORMALIZATION_PARAMS' in data


def test_write_default_config_handles_open_exception(monkeypatch, tmp_path):
    conf = reload_conf()
    p = tmp_path / 'cfg2.json'
    # make open raise
    monkeypatch.setattr(builtins, 'open', lambda *a, **k: (_ for _ in ()).throw(OSError('boom')))
    # should not raise
    conf._write_default_config(str(p))


def test_load_json_config_creates_default_when_missing(monkeypatch, tmp_path):
    conf = reload_conf()
    target = tmp_path / 'missing.json'
    called = {'wrote': False}
    def fake_get():
        return str(target)
    monkeypatch.setattr(conf, '_get_config_path', fake_get)
    def fake_write(path):
        called['wrote'] = True
    monkeypatch.setattr(conf, '_write_default_config', fake_write)
    conf._load_json_config()
    assert called['wrote'] is True


def test_load_json_config_handles_invalid_json(monkeypatch, tmp_path):
    conf = reload_conf()
    target = tmp_path / 'bad.json'
    target.write_text('not json')
    monkeypatch.setattr(conf, '_get_config_path', lambda: str(target))
    # should not raise
    conf._load_json_config()


def test_load_json_config_applies_overrides(monkeypatch, tmp_path):
    conf = reload_conf()
    target = tmp_path / 'good.json'
    payload = {
        'VERSION': '9.9',
        'NORMALIZATION_PARAMS': {'I': -20.0},
        'SUPPORTED_EXTENSIONS': ['.foo'],
        'AUDIO_CODEC': 'aac',
        'AUDIO_BITRATE': '128k',
        'FALLBACK_AUDIO_CODEC': 'ac3',
        'LOG_DIR': 'logsx',
        'LOG_FILE': 'appx.log',
        'LOG_FFMPEG_DEBUG': 'ffx.log',
        'TEMP_SUFFIX': '_t'
    }
    target.write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.setattr(conf, '_get_config_path', lambda: str(target))
    conf._load_json_config()
    assert conf.VERSION == '9.9'
    assert conf.NORMALIZATION_PARAMS.get('I') == -20.0
    assert conf.SUPPORTED_EXTENSIONS == tuple(['.foo'])
    assert conf.AUDIO_CODEC == 'aac'


def test_get_config_path_when_frozen(monkeypatch, tmp_path):
    # simulate a frozen executable location
    import sys as _sys
    fake_exe = str(tmp_path / 'app.exe')
    monkeypatch.setattr(_sys, 'frozen', True, raising=False)
    monkeypatch.setattr(_sys, 'executable', fake_exe, raising=False)
    conf = reload_conf()
    p = conf._get_config_path()
    import os
    assert p == os.path.join(os.path.dirname(fake_exe), 'config.json')


def test_load_json_config_handles_bad_param_values(monkeypatch, tmp_path):
    conf = reload_conf()
    target = tmp_path / 'badparam.json'
    payload = {
        'NORMALIZATION_PARAMS': {'I': 'not-a-number'}
    }
    target.write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.setattr(conf, '_get_config_path', lambda: str(target))
    # reload should not raise and should leave the default numeric value in place
    conf._load_json_config()
    assert isinstance(conf.NORMALIZATION_PARAMS.get('I'), float)
