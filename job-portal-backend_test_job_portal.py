import pytest
import json
from app import app as job_app

@pytest.fixture
def client():
    job_app.config['TESTING'] = True
    with job_app.test_client() as client:
        yield client

def test_jobs_endpoint(client):
    response = client.get('/api/jobs')
    assert response.status_code == 200

def test_resume_upload(client):
    # Test resume upload with mock file
    data = {
        'resume': (open('test_resume.pdf', 'rb'), 'test_resume.pdf')
    }
    response = client.post('/api/upload-resume', data=data)
    assert response.status_code in [200, 400]  # 400 if no file