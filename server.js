const express = require('express');
const axios = require('axios');
const cors = require('cors');

require('dotenv').config();

const app = express();

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

let db = null;
let admin = null;

if (process.env.FIREBASE_PROJECT_ID && process.env.FIREBASE_PRIVATE_KEY && process.env.FIREBASE_CLIENT_EMAIL) {
  try {
    admin = require('firebase-admin');
    admin.initializeApp({
      credential: admin.credential.cert({
        projectId: process.env.FIREBASE_PROJECT_ID,
        privateKey: process.env.FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n'),
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
      }),
    });
    db = admin.firestore();
    console.log('✅ Firebase initialized');
  } catch (error) {
    console.error('❌ Firebase error:', error.message);
  }
}

// ============================================
// Routes
// ============================================

app.get('/', (req, res) => {
  res.json({
    message: 'RVC API Server is running',
    status: 'active',
    timestamp: new Date().toISOString()
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// ============================================
// TEST MODE: يعيد نجاح مباشرة بدون Colab
// ============================================
app.post('/api/train', async (req, res) => {
  try {
    console.log('📥 Training request received:');
    console.log('Body:', JSON.stringify(req.body, null, 2));

    const {
      exp_dir1, trainset_dir4, sr2, if_f0_3, spk_id5, np7,
      f0method8, save_epoch10, total_epoch11, batch_size12,
      if_save_latest13, pretrained_G14, pretrained_D15, gpus16,
      if_cache_gpu17, if_save_every_weights18, version19, gpus_rmvpe,
      user_id
    } = req.body;

    // التحقق من البيانات المطلوبة
    if (!exp_dir1 || !trainset_dir4 || !user_id) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: exp_dir1, trainset_dir4, or user_id'
      });
    }

    console.log('✅ All data received successfully!');
    console.log('- Voice Name:', exp_dir1);
    console.log('- Audio URL:', trainset_dir4);
    console.log('- User ID:', user_id);

    // ✅ يعيد نجاح فوري بدون الاتصال بـ Colab
    const mockResult = {
      success: true,
      message: 'Training request received successfully (TEST MODE)',
      voice_name: exp_dir1,
      audio_url: trainset_dir4,
      received_params: {
        sr2, if_f0_3, spk_id5, np7, f0method8, 
        save_epoch10, total_epoch11, batch_size12
      },
      timestamp: new Date().toISOString(),
      note: 'No actual training - test mode only'
    };

    // حفظ في Firestore إذا كان متاحاً
    if (db && admin) {
      try {
        await db.collection('exp_dir').doc(user_id)
          .collection('voices').doc(exp_dir1)
          .set({
            userId: user_id,
            exp_dir: exp_dir1,
            audioUrl: trainset_dir4,
            status: 'test_completed',
            result: mockResult,
            test_mode: true,
            completedAt: admin.firestore.FieldValue.serverTimestamp()
          }, { merge: true });
        console.log('✅ Saved to Firestore');
      } catch (dbError) {
        console.error('❌ Firestore error:', dbError.message);
      }
    }

    console.log('🎉 Sending success response to Flutter');

    res.json({
      success: true,
      message: 'Training completed successfully (TEST MODE)',
      data: mockResult
    });

  } catch (error) {
    console.error('❌ Error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// ============================================
// Conversion endpoint (TEST MODE)
// ============================================
app.post('/api/convert', async (req, res) => {
  try {
    console.log('📥 Conversion request received:', req.body);
    
    res.json({
      success: true,
      message: 'Conversion request received (TEST MODE)',
      data: {
        ...req.body,
        timestamp: new Date().toISOString()
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log('=================================');
  console.log(`🚀 RVC API Server - TEST MODE`);
  console.log(`🌐 URL: https://rvc-voice-api.onrender.com`);
  console.log(`📊 Health: https://rvc-voice-api.onrender.com/health`);
  console.log(`⚠️  NO COLAB - Test mode only`);
  console.log('=================================');
});
