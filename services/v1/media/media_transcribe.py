import os
import warnings
from faster_whisper import WhisperModel
import srt
from datetime import timedelta
from services.file_management import download_file
import logging
import json

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set the default local storage directory
STORAGE_PATH = "/tmp/"

# Filter out warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

def process_transcribe_media(media_url, task, include_text, include_srt, include_segments, word_timestamps, response_type, language, job_id):
    """Transcribe or translate media using faster-whisper."""
    logger.info(f"Starting {task} for media URL: {media_url}")
    input_filename = download_file(media_url, os.path.join(STORAGE_PATH, 'input_media'))
    logger.info(f"Downloaded media to local file: {input_filename}")

    try:
        # Load model with optimized settings for Neoverse-N1
        model_size = "base"
        # Use 2 threads (leaving 1 core free), compute_type=int8 for better performance
        model = WhisperModel(model_size, device="cpu", compute_type="int8", num_workers=2)
        logger.info(f"Loaded faster-whisper {model_size} model")

        # Configure transcription options
        beam_size = 3  # Reduced beam size for faster processing
        language = language if language else None
        
        # Transcribe with optimized settings
        segments, info = model.transcribe(
            input_filename,
            beam_size=beam_size,
            language=language,
            word_timestamps=word_timestamps,
            condition_on_previous_text=False,  # Disable for faster processing
            vad_filter=True  # Enable voice activity detection for better accuracy
        )
        
        logger.info(f"Generated {task} output with language: {info.language}")

        # Process results
        result = {
            "text": None,
            "srt": None,
            "segments": None,
            "detected_language": info.language
        }

        # Convert segments to list for processing
        segments_list = list(segments)

        if include_text:
            result["text"] = " ".join([seg.text for seg in segments_list])

        if include_srt:
            # Create SRT subtitles
            subtitles = []
            for i, segment in enumerate(segments_list, start=1):
                start = timedelta(seconds=segment.start)
                end = timedelta(seconds=segment.end)
                subtitle = srt.Subtitle(
                    index=i,
                    start=start,
                    end=end,
                    content=segment.text.strip()
                )
                subtitles.append(subtitle)
            result["srt"] = srt.compose(subtitles)

        if include_segments:
            segments_json = []
            for seg in segments_list:
                segment_data = {
                    'start': seg.start,
                    'end': seg.end,
                    'text': seg.text
                }
                if word_timestamps and hasattr(seg, 'words') and seg.words:
                    segment_data['words'] = [
                        {
                            'start': word.start,
                            'end': word.end,
                            'word': word.word
                        }
                        for word in seg.words
                    ]
                segments_json.append(segment_data)
            result["segments"] = segments_json

        # Clean up
        try:
            os.remove(input_filename)
            logger.info(f"Cleaned up temporary file: {input_filename}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {input_filename}: {e}")

        if response_type == "direct":
            return result
        else:
            output_files = {}
            
            if include_text and result["text"]:
                text_filename = os.path.join(STORAGE_PATH, f"{job_id}.txt")
                with open(text_filename, 'w') as f:
                    f.write(result["text"])
                output_files["text"] = text_filename
            
            if include_srt and result["srt"]:
                srt_filename = os.path.join(STORAGE_PATH, f"{job_id}.srt")
                with open(srt_filename, 'w') as f:
                    f.write(result["srt"])
                output_files["srt"] = srt_filename
                
            if include_segments and result["segments"]:
                segments_filename = os.path.join(STORAGE_PATH, f"{job_id}.json")
                with open(segments_filename, 'w') as f:
                    json.dump(result["segments"], f, ensure_ascii=False, indent=2)
                output_files["segments"] = segments_filename

            result["output_files"] = output_files
            return result

    except Exception as e:
        logger.error(f"Error in {task}: {str(e)}")
        raise