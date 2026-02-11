from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
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
        print("⚠️ Firebase not configured (missing environment variables)")
        
except Exception as e:
    print(f"❌ Firebase initialization error: {e}")

# ============================================
# Main Routes
# ============================================

@app.route('/')
def home():
    """الصفحة الرئيسية - معلومات عن السيرفر"""
    return jsonify({
        "message": "RVC API Server - TEST MODE ✅",
        "status": "active",
        "mode": "test",
        "firebase_connected": db is not None,
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health (GET)",
            "train": "/api/train (POST)"
        }
    })


@app.route('/health')
def health():
    """فحص صحة السيرفر"""
    return jsonify({
        "status": "ok",
        "mode": "test",
        "timestamp": datetime.now().isoformat()
    })


# ============================================
# Training Route - TEST MODE
# ============================================

@app.route('/api/train', methods=['POST'])
def train():
    """
    تدريب نموذج RVC - وضع الاختبار
    يستقبل الطلب من التطبيق ويرجع نجاح فوراً
    """
    try:
        data = request.get_json()
        print(f"\n{'='*60}")
        print(f"📥 Training request received from Flutter App!")
        print(f"{'='*60}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"{'='*60}")

        # استخراج البيانات
        exp_dir1      = data.get('exp_dir1')
        trainset_dir4 = data.get('trainset_dir4')
        user_id       = data.get('user_id')
        sr2           = data.get('sr2')
        np7           = data.get('np7')
        f0method8     = data.get('f0method8')
        save_epoch10  = data.get('save_epoch10')
        total_epoch11 = data.get('total_epoch11')
        batch_size12  = data.get('batch_size12')

        # التحقق من البيانات الأساسية
        if not all([exp_dir1, trainset_dir4, user_id]):
            print("❌ Missing required fields!")
            return jsonify({
                "success": False,
                "error": "Missing required fields: exp_dir1, trainset_dir4, user_id"
            }), 400

        # عرض البيانات المستلمة
        print(f"\n✅ All data received successfully!")
        print(f"   📝 Voice Name: {exp_dir1}")
        print(f"   🎵 Audio URL: {trainset_dir4[:80]}...")
        print(f"   👤 User ID: {user_id}")
        print(f"   🎚️  Sample Rate: {sr2}")
        print(f"   ⚙️  Parallel Processes: {np7}")
        print(f"   🎼 F0 Method: {f0method8}")
        print(f"   💾 Save Epoch: {save_epoch10}")
        print(f"   🔢 Total Epochs: {total_epoch11}")
        print(f"   📦 Batch Size: {batch_size12}")

        # إنشاء استجابة نجاح
        response_data = {
            "success": True,
            "message": "Training request received successfully! ✅",
            "data": {
                "voice_name": exp_dir1,
                "user_id": user_id,
                "audio_url": trainset_dir4,
                "settings": {
                    "sample_rate": sr2,
                    "parallel_processes": np7,
                    "f0_method": f0method8,
                    "save_epoch": save_epoch10,
                    "total_epochs": total_epoch11,
                    "batch_size": batch_size12
                },
                "status": "received",
                "timestamp": datetime.now().isoformat(),
                "note": "TEST MODE - Request received and validated successfully"
            }
        }

        # حفظ في Firestore
        if db:
            try:
                doc_data = {
                    "userId":       user_id,
                    "exp_dir":      exp_dir1,
                    "audioUrl":     trainset_dir4,
                    "status":       "test_received",
                    "settings": {
                        "sr": sr2,
                        "np": np7,
                        "f0method": f0method8,
                        "save_epoch": save_epoch10,
                        "total_epochs": total_epoch11,
                        "batch_size": batch_size12
                    },
                    "test_mode":    True,
                    "receivedAt":   firestore.SERVER_TIMESTAMP,
                    "timestamp":    datetime.now().isoformat()
                }
                
                db.collection('exp_dir').document(user_id)\
                  .collection('voices').document(exp_dir1)\
                  .set(doc_data, merge=True)
                  
                print("✅ Saved to Firestore successfully!")
            except Exception as db_error:
                print(f"⚠️ Firestore error (non-critical): {db_error}")

        print(f"\n🎉 Sending success response to Flutter App")
        print(f"{'='*60}\n")

        return jsonify(response_data), 200

    except Exception as e:
        print(f"\n❌ Error in train endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/health", "/api/train"]
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
    print("🚀 RVC API Server - TEST MODE")
    print("="*60)
    print(f"🌐 Running on port {port}")
    print(f"🔥 Firebase: {'✅ Connected' if db else '❌ Not configured'}")
    print(f"🧪 Mode: TEST - No Colab connection required")
    print("="*60)
    print("\n📋 Available endpoints:")
    print("   GET  /              - Server info")
    print("   GET  /health        - Health check")
    print("   POST /api/train     - Receive training request")
    print("="*60)
    print("\n⚠️  This is TEST MODE:")
    print("   - Receives requests from Flutter app")
    print("   - Validates data")
    print("   - Saves to Firestore")
    print("   - Returns success immediately")
    print("   - No actual processing/training")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
