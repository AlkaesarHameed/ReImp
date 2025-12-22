"""
PaddleOCR REST API Server with English and Arabic support.
"""
import io
import os
import logging
from flask import Flask, request, jsonify
from PIL import Image
from paddleocr import PaddleOCR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize OCR engines for different languages
ocr_engines = {}

def get_ocr_engine(lang: str) -> PaddleOCR:
    """Get or create OCR engine for specified language."""
    if lang not in ocr_engines:
        logger.info(f"Initializing OCR engine for language: {lang}")
        ocr_engines[lang] = PaddleOCR(
            lang=lang,
            use_angle_cls=True,
            use_gpu=False
        )
    return ocr_engines[lang]

# Pre-initialize engines on startup
logger.info("Pre-loading OCR engines...")
get_ocr_engine('en')
get_ocr_engine('ar')
logger.info("OCR engines loaded successfully")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'languages': list(ocr_engines.keys())
    })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API info."""
    return jsonify({
        'service': 'PaddleOCR API',
        'version': '1.0.0',
        'status': 'UP',
        'supported_languages': ['en', 'ar', 'ch', 'fr', 'de', 'es', 'it', 'pt', 'ru'],
        'endpoints': {
            'POST /ocr': 'Perform OCR on uploaded image',
            'GET /health': 'Health check'
        }
    })


@app.route('/ocr', methods=['POST'])
def ocr():
    """
    Perform OCR on uploaded image.

    Form parameters:
        - file: Image file (required)
        - lang: Language code (optional, default: 'en')
                Supported: en, ar, ch, fr, de, es, it, pt, ru, etc.

    Returns:
        JSON with OCR results including text, confidence, and bounding boxes.
    """
    # Check for file
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Get language parameter
    lang = request.form.get('lang', 'en')

    try:
        # Read and process image
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Get OCR engine
        ocr_engine = get_ocr_engine(lang)

        # Perform OCR
        import numpy as np
        image_array = np.array(image)
        result = ocr_engine.ocr(image_array, cls=True)

        # Format results
        ocr_results = []
        full_text = []

        if result and result[0]:
            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = float(line[1][1])

                ocr_results.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': {
                        'top_left': bbox[0],
                        'top_right': bbox[1],
                        'bottom_right': bbox[2],
                        'bottom_left': bbox[3]
                    }
                })
                full_text.append(text)

        return jsonify({
            'success': True,
            'language': lang,
            'text': '\n'.join(full_text),
            'results': ocr_results,
            'line_count': len(ocr_results)
        })

    except Exception as e:
        logger.error(f"OCR error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/ocr/multi', methods=['POST'])
def ocr_multi():
    """
    Perform OCR with multiple languages (tries each and returns best result).

    Form parameters:
        - file: Image file (required)
        - languages: Comma-separated language codes (optional, default: 'en,ar')
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    languages = request.form.get('languages', 'en,ar').split(',')

    try:
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))

        if image.mode != 'RGB':
            image = image.convert('RGB')

        import numpy as np
        image_array = np.array(image)

        best_result = None
        best_confidence = 0
        best_lang = None

        for lang in languages:
            lang = lang.strip()
            try:
                ocr_engine = get_ocr_engine(lang)
                result = ocr_engine.ocr(image_array, cls=True)

                if result and result[0]:
                    avg_confidence = sum(line[1][1] for line in result[0]) / len(result[0])
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_result = result
                        best_lang = lang
            except Exception as e:
                logger.warning(f"Error with language {lang}: {e}")
                continue

        if best_result and best_result[0]:
            ocr_results = []
            full_text = []

            for line in best_result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = float(line[1][1])

                ocr_results.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': {
                        'top_left': bbox[0],
                        'top_right': bbox[1],
                        'bottom_right': bbox[2],
                        'bottom_left': bbox[3]
                    }
                })
                full_text.append(text)

            return jsonify({
                'success': True,
                'detected_language': best_lang,
                'average_confidence': best_confidence,
                'text': '\n'.join(full_text),
                'results': ocr_results,
                'line_count': len(ocr_results)
            })

        return jsonify({
            'success': True,
            'text': '',
            'results': [],
            'line_count': 0
        })

    except Exception as e:
        logger.error(f"Multi-OCR error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=False)
