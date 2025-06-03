import os
from starlette.responses import StreamingResponse
from starlette.requests import Request
from starlette.exceptions import HTTPException

from google.cloud import storage

# 환경 변수에서 GCP 프로젝트와 버킷 이름을 가져옵니다.
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GCS_BUCKET = os.getenv("GCS_BUCKET")

if not GCS_BUCKET:
    raise RuntimeError("GCS_BUCKET 환경 변수가 설정되어 있지 않습니다.")

async def get_bucket_file(request: Request):
    '''
    GCP Object Storage(GCS)에서 파일을 읽어 제공하는 엔드포인트
    example: http://localhost:9999/buckets/goog-10-k-2024.pdf#page=11
    '''
    filepath = request.path_params["filepath"]
    try:
        client = storage.Client(project=GCP_PROJECT) if GCP_PROJECT else storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(filepath)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found in bucket.")
        stream = blob.open("rb")
        return StreamingResponse(
            stream,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{os.path.basename(filepath)}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
