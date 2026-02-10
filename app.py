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
    firebase_project_id = os.environ.get('FIREBASE_PROJECT_ID')
    firebase_private_key = os.environ.get('FIREBASE_PRIVATE_KEY')
    firebase_client_email = os.environ.get('FIREBASE_CLIENT_EMAIL')
    
    if all([firebase_project_id, firebase_private_key, firebase_client_email]):
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": firebase_project_id,
            "private_key": firebase_private_key.replace('\\n', '\n'),
            "client_email": firebase_client_email,
        })
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase initialized")
    else:
        print("⚠️ Firebase not configured")
        
except Exception as e:
    print(f"❌ Firebase error: {e}")

# ============================================
# Colab URL (يتم تحديثه من Colab عبر /api/register-colab)
# ============================================
COLAB_URL = None

# ============================================
# Routes
# ============================================

@app.route('/')
def home():
    return jsonify({
        "message": "RVC API Server is running (Python/Flask)",
        "status": "active",
        "colab_connected": COLAB_URL is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})


# ============================================
# Colab يرسل رابطه هنا عند بدء التشغيل
# ============================================
@app.route('/api/register-colab', methods=['POST'])
def register_colab():
    global COLAB_URL
    data = request.get_json()
    colab_url = data.get('colab_url')
    
    if not colab_url:
        return jsonify({"success": False, "error": "colab_url is required"}), 400
    
    COLAB_URL = colab_url.rstrip('/')
    print(f"✅ Colab registered: {COLAB_URL}")
    
    return jsonify({
        "success": True,
        "message": "Colab URL registered successfully",
        "colab_url": COLAB_URL
    })


# ============================================
# Route: Preprocess - يرسل الطلب لـ Colab
# ============================================
@app.route('/api/preprocess', methods=['POST'])
def preprocess():
    global COLAB_URL
    try:
        data = request.get_json()
        print(f"📥 Preprocess request received: {data}")

        # استخراج البيانات المطلوبة
        trainset_dir = data.get('trainset_dir')   # مسار ملفات الصوت
        exp_dir      = data.get('exp_dir')         # اسم المشروع / الصوت
        sr           = data.get('sr', '40k')       # sample rate: 32k / 40k / 48k
        n_p          = data.get('n_p', 2)          # عدد العمليات المتوازية
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
                "error": "Colab is not connected. Please run the Colab notebook first."
            }), 503

        # إرسال الطلب إلى Colab
        colab_payload = {
            "trainset_dir": trainset_dir,
            "exp_dir":      exp_dir,
            "sr":           sr,
            "n_p":          n_p,
            "user_id":      user_id
        }

        print(f"📤 Sending to Colab: {COLAB_URL}/preprocess")
        colab_response = requests.post(
            f"{COLAB_URL}/preprocess",
            json=colab_payload,
            timeout=300   # 5 دقائق كحد أقصى
        )

        colab_data = colab_response.json()
        print(f"📨 Colab response: {colab_data}")

        # حفظ النتيجة في Firestore
        if db:
            try:
                db.collection('exp_dir').document(user_id)\
                  .collection('voices').document(exp_dir)\
                  .set({
                      "userId":       user_id,
                      "exp_dir":      exp_dir,
                      "trainset_dir": trainset_dir,
                      "sr":           sr,
                      "n_p":          n_p,
                      "status":       "preprocessed" if colab_data.get("success") else "failed",
                      "colab_result": colab_data,
                      "updatedAt":    firestore.SERVER_TIMESTAMP
                  }, merge=True)
                print("✅ Saved to Firestore")
            except Exception as db_error:
                print(f"❌ Firestore error: {db_error}")

        return jsonify({
            "success": colab_data.get("success", False),
            "message": "Preprocess completed via Colab",
            "data":    colab_data
        }), colab_response.status_code

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Colab request timed out (>5 min)"
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "Cannot connect to Colab. Make sure the notebook is running."
        }), 503

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# Route: Train (محدّث ليرسل لـ Colab أيضاً)
# ============================================
@app.route('/api/train', methods=['POST'])
def train():
    global COLAB_URL
    try:
        data = request.get_json()
        print(f"📥 Training request received: {data}")

        exp_dir1      = data.get('exp_dir1')
        trainset_dir4 = data.get('trainset_dir4')
        user_id       = data.get('user_id')

        if not all([exp_dir1, trainset_dir4, user_id]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        if not COLAB_URL:
            return jsonify({
                "success": False,
                "error": "Colab is not connected."
            }), 503

        colab_payload = {
            "exp_dir1":      exp_dir1,
            "trainset_dir4": trainset_dir4,
            "user_id":       user_id
        }

        colab_response = requests.post(
            f"{COLAB_URL}/train",
            json=colab_payload,
            timeout=600
        )
        colab_data = colab_response.json()

        if db:
            try:
                db.collection('exp_dir').document(user_id)\
                  .collection('voices').document(exp_dir1)\
                  .set({
                      "userId":       user_id,
                      "exp_dir":      exp_dir1,
                      "audioUrl":     trainset_dir4,
                      "status":       "trained" if colab_data.get("success") else "failed",
                      "colab_result": colab_data,
                      "updatedAt":    firestore.SERVER_TIMESTAMP
                  }, merge=True)
            except Exception as db_error:
                print(f"❌ Firestore error: {db_error}")

        return jsonify({
            "success": colab_data.get("success", False),
            "message": "Training completed via Colab",
            "data":    colab_data
        })

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/convert', methods=['POST'])
def convert():
    try:
        data = request.get_json()
        print(f"📥 Conversion request: {data}")
        return jsonify({
            "success": True,
            "message": "Conversion received (TEST MODE)",
            "data": {**data, "timestamp": datetime.now().isoformat()}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# Run Server
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print("=================================")
    print(f"🚀 RVC API Server - Python/Flask")
    print(f"🌐 Running on port {port}")
    print("=================================")
    app.run(host='0.0.0.0', port=port, debug=False)
