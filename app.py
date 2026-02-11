
@app.route('/')
def home():
    return jsonify({
        "message": "RVC API Server is running (Python/Flask)",
        "status": "active",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/train', methods=['POST'])
def train():
    try:
        data = request.get_json()
        print(f"📥 Training request received:")
        print(json.dumps(data, indent=2))
        
        # استخراج البيانات
        exp_dir1 = data.get('exp_dir1')
        trainset_dir4 = data.get('trainset_dir4')
        user_id = data.get('user_id')
        
        # التحقق من البيانات
        if not all([exp_dir1, trainset_dir4, user_id]):
            return jsonify({
                "success": False,
                "error": "Missing required fields"
            }), 400
        
        print(f"✅ All data received!")
        print(f"- Voice Name: {exp_dir1}")
        print(f"- Audio URL: {trainset_dir4}")
        print(f"- User ID: {user_id}")
        
        # إنشاء نتيجة وهمية
        mock_result = {
            "success": True,
            "message": "Training request received (Python TEST MODE)",
            "voice_name": exp_dir1,
            "audio_url": trainset_dir4,
            "timestamp": datetime.now().isoformat(),
            "note": "No actual training - test mode only"
        }
        
        # حفظ في Firestore
        if db:
            try:
                db.collection('exp_dir').document(user_id)\
                  .collection('voices').document(exp_dir1)\
                  .set({
                      "userId": user_id,
                      "exp_dir": exp_dir1,
                      "audioUrl": trainset_dir4,
                      "status": "test_completed",
                      "result": mock_result,
                      "test_mode": True,
                      "completedAt": firestore.SERVER_TIMESTAMP
                  }, merge=True)
                print("✅ Saved to Firestore")
            except Exception as db_error:
                print(f"❌ Firestore error: {db_error}")
        
        print("🎉 Sending success response")
        
        return jsonify({
            "success": True,
            "message": "Training completed successfully",
            "data": mock_result
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/convert', methods=['POST'])
def convert():
    try:
        data = request.get_json()
        print(f"📥 Conversion request: {data}")
        
        return jsonify({
            "success": True,
            "message": "Conversion received (TEST MODE)",
            "data": {
                **data,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================
# Run Server
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print("=================================")
    print(f"🚀 RVC API Server - Python/Flask")
    print(f"🌐 Running on port {port}")
    print(f"⚠️  TEST MODE - No Colab")
    print("=================================")
    app.run(host='0.0.0.0', port=port, debug=False)
