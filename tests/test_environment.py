import os
from app.environment import configure_environment


def test_app_drops_unrelated_credentials_and_preserves_google_identity(monkeypatch, tmp_path):
    for name in ['OTHER_API_KEY', 'OTHER_ACCESS_TOKEN', 'OTHER_BASE_URL', 'OTHER_ENDPOINT', 'OTHER_MODEL']:
        monkeypatch.setenv(name, 'unrelated-value')
    monkeypatch.setenv('GEMINI_API_KEY', 'gemini-test-only')
    monkeypatch.setenv('DEMO_ACCESS_TOKEN', 'demo-test-only')
    monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', '/example/google-identity.json')
    monkeypatch.setenv('FIRESTORE_PROJECT_ID', 'example-project')
    configure_environment(tmp_path / 'missing.env')
    assert all(name not in os.environ for name in ['OTHER_API_KEY', 'OTHER_ACCESS_TOKEN', 'OTHER_BASE_URL', 'OTHER_ENDPOINT', 'OTHER_MODEL'])
    assert os.environ['GEMINI_API_KEY'] == 'gemini-test-only'
    assert os.environ['DEMO_ACCESS_TOKEN'] == 'demo-test-only'
    assert os.environ['GOOGLE_APPLICATION_CREDENTIALS'] == '/example/google-identity.json'
    assert os.environ['FIRESTORE_PROJECT_ID'] == 'example-project'


def test_dotenv_only_loads_recognized_project_settings(monkeypatch, tmp_path):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('UNRELATED_API_KEY', raising=False)
    monkeypatch.delenv('UNRELATED_SETTING', raising=False)
    path = tmp_path / '.env'
    path.write_text('GEMINI_API_KEY=gemini-test-only\nUNRELATED_API_KEY=ignored\nUNRELATED_SETTING=ignored\n')
    configure_environment(path)
    assert os.environ['GEMINI_API_KEY'] == 'gemini-test-only'
    assert 'UNRELATED_API_KEY' not in os.environ
    assert 'UNRELATED_SETTING' not in os.environ
