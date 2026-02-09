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

const COLAB_API_URL = process.env.COLAB_API_URL;
const MOCK_MODE = !COLAB_API_URL; // ⬅️ تفعيل المحاكاة إذا لم يكن هناك COLAB_API_URL

if (MOCK_MODE) {
  console.log('⚠️  MOCK MODE ENABLED - No Colab connection');
  console.log('⚠️  Server will simulate training responses');
} else {
  console.log('✅ COLAB_API_URL configured:', COLAB_API_URL);
}

// ============================================
// Routes
// ============================================

app.get('/', (req, res) => {
  res.json({
    message: 'RVC API Server is running',
    status: 'active',
    mock_mode: MOCK_MODE,
    timestamp: new Date().toISOString()
  });
});

app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok',
    mock_mode: MOCK_MODE 
  });
});

// ============================================
// RVC Training Endpoint
// ============================================
app.post('/api/train', async (req, res) => {
  try {
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

    console.log('📥 Training request:', {
      voiceName: exp_dir1,
      audioUrl: trainset_dir4,
      userId: user_id,
      mode: MOCK_MODE ? 'MOCK' : 'REAL'
    });

    // 🔴 وضع المحاكاة - إذا لم يكن هناك Colab
    if (MOCK_MODE) {
      console.log('🎭 Simulating training process...');
      
      // محاكاة تأخير التدريب (5 ثواني)
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      const mockResult = {
        success: true,
        message: 'Training completed (MOCK MODE)',
        model_path: `models/${exp_dir1}/${exp_dir1}_e200.pth`,
        index_path: `models/${exp_dir1}/added_IVF1024_Flat_nprobe_1_${exp_dir1}_v2.index`,
        sample_rate: sr2 || 40000,
        epochs: total_epoch11 || 200,
        training_time: '45.2 seconds (mock)',
        mock: true
      };

      console.log('✅ Mock training completed');

      // حفظ في Firestore إذا كان متاحاً
      if (db && admin) {
        try {
          await db.collection('exp_dir').doc(user_id)
            .collection('voices').doc(exp_dir1)
            .set({
              userId: user_id,
              exp_dir: exp_dir1,
              audioUrl: trainset_dir4,
              status: 'completed',
              result: mockResult,
              mock: true,
              completedAt: admin.firestore.FieldValue.serverTimestamp()
            }, { merge: true });
          console.log('✅ Saved to Firestore');
        } catch (dbError) {
          console.error('❌ Firestore error:', dbError.message);
        }
      }

      return res.json({
        success: true,
        message: 'Training completed (MOCK MODE)',
        data: mockResult
      });
    }

    // 🔴 وضع حقيقي - إرسال لـ Colab
    console.log('🚀 Sending to Colab...');
    
    const trainingResponse = await axios.post(`${COLAB_API_URL}/train`, {
      exp_dir1, trainset_dir4, sr2, if_f0_3, spk_id5, np7,
      f0method8, save_epoch10, total_epoch11, batch_size12,
      if_save_latest13, pretrained_G14, pretrained_D15, gpus16,
      if_cache_gpu17, if_save_every_weights18, version19, gpus_rmvpe,
      user_id
    }, {
      timeout: 600000,
      headers: { 'Content-Type': 'application/json' }
    });

    console.log('✅ Colab response received');

    if (db && admin) {
      try {
        await db.collection('exp_dir').doc(user_id)
          .collection('voices').doc(exp_dir1)
          .set({
            userId: user_id,
            exp_dir: exp_dir1,
            audioUrl: trainset_dir4,
            status: 'completed',
            result: trainingResponse.data,
            completedAt: admin.firestore.FieldValue.serverTimestamp()
          }, { merge: true });
      } catch (dbError) {
        console.error('❌ Firestore error:', dbError.message);
      }
    }

    res.json({
      success: true,
      message: 'Training completed',
      data: trainingResponse.data
    });

  } catch (error) {
    console.error('❌ Training error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// ============================================
// RVC Conversion Endpoint
// ============================================
app.post('/api/convert', async (req, res) => {
  try {
    const { audio_url, model_name, pitch, user_id } = req.body;

    if (!audio_url || !model_name) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields'
      });
    }

    // وضع المحاكاة
    if (MOCK_MODE) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      return res.json({
        success: true,
        message: 'Conversion completed (MOCK MODE)',
        output_url: audio_url, // يرجع نفس الصوت في الوضع التجريبي
        mock: true
      });
    }

    // وضع حقيقي
    const response = await axios.post(`${COLAB_API_URL}/convert`, {
      audio_url, model_name, pitch, user_id
    }, {
      timeout: 120000,
      headers: { 'Content-Type': 'application/json' }
    });

    res.json({
      success: true,
      data: response.data
    });

  } catch (error) {
    console.error('❌ Conversion error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log('=================================');
  console.log(`🚀 RVC Voice API Server`);
  console.log(`🌐 URL: https://rvc-voice-api.onrender.com`);
  console.log(`📊 Health: https://rvc-voice-api.onrender.com/health`);
  console.log(MOCK_MODE ? `🎭 MODE: MOCK (No Colab)` : `⚡ MODE: REAL (With Colab)`);
  console.log('=================================');
});
