from flask import Blueprint
from app_utils import *
import logging
import os
from services.v1.media.media_transcribe import process_transcribe_media
from services.authentication import authenticate
from services.cloud_storage import upload_file
import json

v1_media_transcribe_bp = Blueprint('v1_media_transcribe', __name__)
logger = logging.getLogger(__name__)

@v1_media_transcribe_bp.route('/v1/media/transcribe', methods=['POST'])
@authenticate
@validate_payload({
    "type": "object",
    "properties": {
        "media_url": {"type": "string", "format": "uri"},
        "task": {"type": "string", "enum": ["transcribe", "translate"]},
        "include_text": {"type": "boolean"},
        "include_srt": {"type": "boolean"},
        "include_segments": {"type": "boolean"},
        "word_timestamps": {"type": "boolean"},
        "response_type": {"type": "string", "enum": ["direct", "cloud"]},
        "language": {"type": "string"},
        "webhook_url": {"type": "string", "format": "uri"},
        "id": {"type": "string"}
    },
    "required": ["media_url"],
    "additionalProperties": False
})
@queue_task_wrapper(bypass_queue=False)
def transcribe(job_id, data):
    media_url = data['media_url']
    task = data.get('task', 'transcribe')
    include_text = data.get('include_text', True)
    include_srt = data.get('include_srt', False)
    include_segments = data.get('include_segments', False)
    word_timestamps = data.get('word_timestamps', False)
    response_type = data.get('response_type', 'direct')
    language = data.get('language', None)
    webhook_url = data.get('webhook_url')
    id = data.get('id')

    logger.info(f"Job {job_id}: Received transcription request for {media_url}")

    try:
        result = process_transcribe_media(
            media_url=media_url,
            task=task,
            include_text=include_text,
            include_srt=include_srt,
            include_segments=include_segments,
            word_timestamps=word_timestamps,
            response_type=response_type,
            language=language,
            job_id=job_id
        )
        logger.info(f"Job {job_id}: Transcription process completed successfully")

        if response_type == "direct":
            # Return the results directly
            return {
                "text": result["text"],
                "srt": result["srt"],
                "segments": result["segments"],
                "detected_language": result["detected_language"],
                "text_url": None,
                "srt_url": None,
                "segments_url": None,
            }, "/v1/transcribe/media", 200
        else:
            # Upload results to cloud storage
            text_url = None
            srt_url = None
            segments_url = None

            if "output_files" in result:
                if "text" in result["output_files"]:
                    text_url = upload_file(result["output_files"]["text"])
                    os.remove(result["output_files"]["text"])

                if "srt" in result["output_files"]:
                    srt_url = upload_file(result["output_files"]["srt"])
                    os.remove(result["output_files"]["srt"])

                if "segments" in result["output_files"]:
                    segments_url = upload_file(result["output_files"]["segments"])
                    os.remove(result["output_files"]["segments"])

            return {
                "text": None,
                "srt": None,
                "segments": None,
                "detected_language": result["detected_language"],
                "text_url": text_url,
                "srt_url": srt_url,
                "segments_url": segments_url,
            }, "/v1/transcribe/media", 200

    except Exception as e:
        logger.error(f"Job {job_id}: Error during transcription process - {str(e)}")
        return str(e), "/v1/transcribe/media", 500
