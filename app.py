from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# Firebase Initialization
# ============================================
db = None

try:
    # استخدام متغير واحد يحتوي على كل بيانات Service Account
    firebase_service_account = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    
    if firebase_service_account:
        # تحويل النص إلى JSON
        service_account_info = json.loads(firebase_service_account)
        
        # التحقق من وجود البيانات المطلوبة
        required_fields = ['type', 'project_id', 'private_key', 'client_email', 'token_uri']
        missing_fields = [field for field in required_fields if field not in service_account_info]
        
        if missing_fields:
            print(f"⚠️ Firebase config missing fields: {missing_fields}")
        else:
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase initialized successfully")
    else:
        print("⚠️ FIREBASE_SERVICE_ACCOUNT environment variable not found")
        
except json.JSONDecodeError as je:
    print(f"❌ Firebase config is not valid JSON: {je}")
except Exception as e:
    print(f"❌ Firebase initialization error: {e}")
# ============================================
# Colab URL (يتم تحديثه من Colab عبر /api/register-colab)
# ============================================
COLAB_URL = None
COLAB_REGISTERED_AT = None

# ============================================
# Main Routes
# ============================================

@app.route('/')
def home():
    """الصفحة الرئيسية - معلومات عن السيرفر"""
    return jsonify({
        "message": "RVC API Server is running (Python/Flask)",
        "status": "active",
        "colab_connected": COLAB_URL is not None,
        "colab_url": COLAB_URL if COLAB_URL else None,
        "colab_registered_at": COLAB_REGISTERED_AT,
        "firebase_connected": db is not None,
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "register_colab": "/api/register-colab (POST)",
            "colab_status": "/api/colab-status (GET)",
            "test_colab": "/api/test-colab-connection (GET)",
            "preprocess": "/api/preprocess (POST)",
            "train": "/api/train (POST)",
            "convert": "/api/convert (POST)"
        }
    })


@app.route('/health')
def health():
    """فحص صحة السيرفر"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })


# ============================================
# Colab Management Routes
# ============================================

@app.route('/api/register-colab', methods=['POST'])
def register_colab():
    """
    Colab يرسل رابطه هنا عند بدء التشغيل
    
    Expected payload:
    {
        "colab_url": "https://xxxx.ngrok-free.app"
    }
    """
    global COLAB_URL, COLAB_REGISTERED_AT
    
    try:
        data = request.get_json()
        colab_url = data.get('colab_url')
        
        if not colab_url:
            return jsonify({
                "success": False,
                "error": "colab_url is required"
            }), 400
        
        # تنظيف الرابط
        COLAB_URL = colab_url.rstrip('/')
        COLAB_REGISTERED_AT = datetime.now().isoformat()
        
        print(f"✅ Colab registered: {COLAB_URL}")
        print(f"   Registered at: {COLAB_REGISTERED_AT}")
        
        # محاولة التحقق من الاتصال
        try:
            test_response = requests.get(f"{COLAB_URL}/health", timeout=5)
            colab_health = test_response.json()
            print(f"   Colab health check: {colab_health}")
        except Exception as e:
            print(f"   ⚠️ Could not verify Colab health: {e}")
        
        return jsonify({
            "success": True,
            "message": "Colab URL registered successfully",
            "colab_url": COLAB_URL,
            "registered_at": COLAB_REGISTERED_AT
        })
        
    except Exception as e:
        print(f"❌ Error registering Colab: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/colab-status', methods=['GET'])
def colab_status():
    """
    الحصول على حالة Colab الحالية
    """
    return jsonify({
        "colab_connected": COLAB_URL is not None,
        "colab_url": COLAB_URL,
        "registered_at": COLAB_REGISTERED_AT,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/test-colab-connection', methods=['GET'])
def test_colab():
    """
    اختبار الاتصال مع Colab
    """
    global COLAB_URL
    
    if not COLAB_URL:
        return jsonify({
            "success": False,
            "error": "Colab is not registered. Please run the Colab notebook first.",
            "colab_url": None,
            "registered_at": None
        }), 503
    
    try:
        # محاولة الوصول لـ /health في Colab
        print(f"🔍 Testing connection to: {COLAB_URL}/health")
        response = requests.get(f"{COLAB_URL}/health", timeout=10)
        colab_health = response.json()
        
        print(f"✅ Colab responded: {colab_health}")
        
        return jsonify({
            "success": True,
            "message": "Colab is connected and responding",
            "colab_url": COLAB_URL,
            "colab_health": colab_health,
            "registered_at": COLAB_REGISTERED_AT,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Colab connection timeout")
        return jsonify({
            "success": False,
            "error": "Connection to Colab timed out",
            "colab_url": COLAB_URL
        }), 504
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Cannot connect to Colab: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot reach Colab. The ngrok tunnel may have expired.",
            "colab_url": COLAB_URL,
            "details": str(e)
        }), 503
        
    except Exception as e:
        print(f"❌ Error testing Colab: {e}")
        return jsonify({
            "success": False,
            "error": f"Error: {str(e)}",
            "colab_url": COLAB_URL
        }), 500


@app.route('/api/disconnect-colab', methods=['POST'])
def disconnect_colab():
    """
    فصل Colab (للاستخدام اليدوي أو عند إعادة التشغيل)
    """
    global COLAB_URL, COLAB_REGISTERED_AT
    
    old_url = COLAB_URL
    COLAB_URL = None
    COLAB_REGISTERED_AT = None
    
    print(f"🔌 Colab disconnected: {old_url}")
    
    return jsonify({
        "success": True,
        "message": "Colab disconnected",
        "previous_url": old_url
    })


# ============================================
# RVC Processing Routes
# ============================================

@app.route('/api/preprocess', methods=['POST'])
def preprocess():
    """
    معالجة ملفات الصوت قبل التدريب
    يرسل الطلب إلى Colab
    
    Expected payload:
    {
        "trainset_dir": "/path/to/audio/files",
        "exp_dir": "model_name",
        "sr": "40k",  // optional: 32k, 40k, 48k
        "n_p": 2,     // optional: number of parallel processes
        "user_id": "user_123"
    }
    """
    global COLAB_URL
    
    try:
        data = request.get_json()
        print(f"\n📥 Preprocess request received:")
        print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}")

        # استخراج البيانات المطلوبة
        trainset_dir = data.get('trainset_dir')
        exp_dir      = data.get('exp_dir')
        sr           = data.get('sr', '40k')
        n_p          = data.get('n_p', 2)
        user_id      = data.get('user_id')

        # التحقق من البيانات الأساسية
        if not all([trainset_dir, exp_dir, user_id]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: trainset_dir, exp_dir, user_id"
            }), 400

        # التحقق من اتصال Colab
        if not COLAB_URL:
            return jsonify({
                "success": False,
                "error": "Colab is not connected. Please run the Colab notebook first.",
                "hint": "Run all cells in the Colab notebook and wait for 'Colab is ready' message"
            }), 503

        # إعداد البيانات للإرسال إلى Colab
        colab_payload = data

        print(f"📤 Sending to Colab: {COLAB_URL}/preprocess")
        print(f"   Payload: {json.dumps(colab_payload, indent=2)}")
        
        # إرسال الطلب إلى Colab
        colab_response = requests.post(
            f"{COLAB_URL}/preprocess",
            json=colab_payload,
            timeout=300  # 5 دقائق كحد أقصى
        )

        colab_data = colab_response.json()
        print(f"📨 Colab response ({colab_response.status_code}):")
        print(f"   {json.dumps(colab_data, indent=2, ensure_ascii=False)}")

        # حفظ النتيجة في Firestore
        if db:
            try:
                doc_data = {
                    "userId":       user_id,
                    "exp_dir":      exp_dir,
                    "trainset_dir": trainset_dir,
                    "sr":           sr,
                    "n_p":          int(n_p),
                    "status":       "preprocessed" if colab_data.get("success") else "failed",
                    "colab_result": colab_data,
                    "updatedAt":    firestore.SERVER_TIMESTAMP,
                    "processedAt":  datetime.now().isoformat()
                }
                
                db.collection('exp_dir').document(user_id)\
                  .collection('voices').document(exp_dir)\
                  .set(doc_data, merge=True)
                  
                print("✅ Saved to Firestore")
            except Exception as db_error:
                print(f"❌ Firestore error: {db_error}")

        # إرجاع النتيجة للعميل
        return jsonify({
            "success": colab_data.get("success", False),
            "message": "Preprocessing request sent to Colab",
            "data": colab_data,
            "timestamp": datetime.now().isoformat()
        }), colab_response.status_code

    except requests.exceptions.Timeout:
        error_msg = "Colab request timed out (>5 minutes). The preprocessing may still be running."
        print(f"⏱️ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 504

    except requests.exceptions.ConnectionError as e:
        error_msg = "Cannot connect to Colab. The ngrok tunnel may have expired."
        print(f"❌ {error_msg}: {e}")
        return jsonify({
            "success": False,
            "error": error_msg,
            "hint": "Please restart the Colab notebook and wait for the new ngrok URL"
        }), 503

    except Exception as e:
        print(f"❌ Unexpected error in preprocess: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/train', methods=['POST'])
def train():
    """
    تدريب نموذج RVC
    يرسل الطلب إلى Colab
    
    Expected payload:
    {
        "exp_dir1": "model_name",
        "trainset_dir4": "/path/to/audio",
        "user_id": "user_123"
    }
    """
    global COLAB_URL
    
    try:
        data = request.get_json()
        print(f"\n📥 Training request received:")
        print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}")

        exp_dir1      = data.get('exp_dir1')
        trainset_dir4 = data.get('trainset_dir4')
        user_id       = data.get('user_id')

        if not all([exp_dir1, trainset_dir4, user_id]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: exp_dir1, trainset_dir4, user_id"
            }), 400

        if not COLAB_URL:
            return jsonify({
                "success": False,
                "error": "Colab is not connected. Please run the Colab notebook first."
            }), 503

        colab_payload = data

        print(f"📤 Sending to Colab: {COLAB_URL}/train")
        
        colab_response = requests.post(
            f"{COLAB_URL}/train",
            json=colab_payload,
            timeout=600  # 10 دقائق للتدريب
        )
        
        colab_data = colab_response.json()
        print(f"📨 Colab response: {json.dumps(colab_data, indent=2, ensure_ascii=False)}")

        # حفظ في Firestore
        if db:
            try:
                doc_data = {
                    "userId":       user_id,
                    "exp_dir":      exp_dir1,
                    "audioUrl":     trainset_dir4,
                    "status":       "trained" if colab_data.get("success") else "failed",
                    "colab_result": colab_data,
                    "updatedAt":    firestore.SERVER_TIMESTAMP,
                    "trainedAt":    datetime.now().isoformat()
                }
                
                db.collection('exp_dir').document(user_id)\
                  .collection('voices').document(exp_dir1)\
                  .set(doc_data, merge=True)
                  
                print("✅ Saved to Firestore")
            except Exception as db_error:
                print(f"❌ Firestore error: {db_error}")

        return jsonify({
            "success": colab_data.get("success", False),
            "message": "Training request sent to Colab",
            "data": colab_data,
            "timestamp": datetime.now().isoformat()
        }), colab_response.status_code

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Training request timed out (>10 minutes)"
        }), 504
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "Cannot connect to Colab"
        }), 503
        
    except Exception as e:
        print(f"❌ Error in train: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/convert', methods=['POST'])
def convert():
    global COLAB_URL

    try:
        data = request.get_json()
        print(f"\n📥 Convert request received:")
        print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}")

        if not COLAB_URL:
            return jsonify({
                "success": False,
                "error": "Colab is not connected."
            }), 503

        colab_response = requests.post(
            f"{COLAB_URL}/convert",
            json=data,
            timeout=300
        )

        colab_data = colab_response.json()
        print(f"📨 Colab response: {json.dumps(colab_data, indent=2)}")

        return jsonify({
            "success": colab_data.get("success", False),
            "message": "Convert request processed",
            "data":    colab_data,
            "timestamp": datetime.now().isoformat()
        }), colab_response.status_code

    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "Colab timed out"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Cannot connect to Colab"}), 503
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "message": "Please check the API documentation"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": str(e)
    }), 500


# ============================================
# Run Server
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    
    print("\n" + "="*60)
    print("🚀 RVC API Server - Python/Flask")
    print("="*60)
    print(f"🌐 Running on port {port}")
    print(f"🔥 Firebase: {'✅ Connected' if db else '❌ Not configured'}")
    print(f"🔗 Colab: {'✅ Will connect when notebook runs' if not COLAB_URL else f'Already connected to {COLAB_URL}'}")
    print("="*60)
    print("\n📋 Available endpoints:")
    print("   GET  /              - Server info")
    print("   GET  /health        - Health check")
    print("   POST /api/register-colab       - Register Colab URL")
    print("   GET  /api/colab-status         - Check Colab status")
    print("   GET  /api/test-colab-connection - Test Colab connection")
    print("   POST /api/disconnect-colab     - Disconnect Colab")
    print("   POST /api/preprocess           - Preprocess audio")
    print("   POST /api/train                - Train model")
    print("   POST /api/convert              - Convert audio")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
