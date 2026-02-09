const express = require('express');
const axios = require('axios');
const cors = require('cors');

// 🔴 مهم: تحميل متغيرات البيئة أولاً
require('dotenv').config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// 🔴 تهيئة Firebase (إذا كانت متغيرات Firebase موجودة)
let db = null;
let admin = null;

if (process.env.FIREBASE_PROJECT_ID && 
    process.env.FIREBASE_PRIVATE_KEY && 
    process.env.FIREBASE_CLIENT_EMAIL) {
  
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
    console.log('✅ Firebase initialized successfully');
  } catch (error) {
    console.error('❌ Firebase initialization failed:', error.message);
  }
} else {
  console.log('⚠️ Firebase not configured - running without Firestore');
}

// 🔴 التحقق من COLAB_API_URL
const COLAB_API_URL = process.env.COLAB_API_URL;
if (!COLAB_API_URL) {
  console.error('❌ ERROR: COLAB_API_URL is not defined in environment variables');
  console.error('Please set COLAB_API_URL in Render Environment Variables');
} else {
  console.log('✅ COLAB_API_URL configured:', COLAB_API_URL);
}

// ============================================
// Routes
// ============================================

// الصفحة الرئيسية - للتحقق من عمل السيرفر
app.get('/', (req, res) => {
  res.json({
    message: 'RVC Voice API Server is running!',
    status: 'active',
    timestamp: new Date().toISOString(),
    firebase_connected: db !== null,
    colab_configured: COLAB_API_URL !== undefined
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

// ============================================
// RVC Training Endpoint
// ============================================
app.post('/api/train', async (req, res) => {
  try {
    // 🔴 التحقق من COLAB_API_URL
    if (!COLAB_API_URL) {
      return res.status(500).json({
        success: false,
        error: 'Server configuration error: COLAB_API_URL not set'
      });
    }

    // استقبال جميع البيانات من Flutter
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

    console.log('📥 RVC Training Request:');
    console.log('- Voice Name:', exp_dir1);
    console.log('- Audio URL:', trainset_dir4);
    console.log('- Sample Rate:', sr2);
    console.log('- Total Epochs:', total_epoch11);
    console.log('- User ID:', user_id);

    // 🔴 إرسال إلى Colab
    console.log('🚀 Sending request to Colab...');
    
    const trainingResponse = await axios.post(`${COLAB_API_URL}/train`, {
      exp_dir1, trainset_dir4, sr2, if_f0_3, spk_id5, np7,
      f0method8, save_epoch10, total_epoch11, batch_size12,
      if_save_latest13, pretrained_G14, pretrained_D15, gpus16,
      if_cache_gpu17, if_save_every_weights18, version19, gpus_rmvpe,
      user_id
    }, {
      timeout: 600000, // 10 دقائق للتدريب
      headers: {
        'Content-Type': 'application/json'
      }
    });

    console.log('✅ Training completed:', trainingResponse.data);

    // 🔴 حفظ النتيجة في Firestore (إذا كان متصلاً)
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
        console.log('✅ Result saved to Firestore');
      } catch (dbError) {
        console.error('❌ Firestore save failed:', dbError.message);
        // لا نوقف الرد إذا فشل Firestore
      }
    }

    res.json({
      success: true,
      message: 'Training completed',
      data: trainingResponse.data
    });

  } catch (error) {
    console.error('❌ Training error:', error.message);
    
    // تفاصيل أكثر عن الخطأ
    if (error.response) {
      console.error('Colab response error:', error.response.data);
      return res.status(500).json({
        success: false,
        error: 'Colab server error',
        details: error.response.data
      });
    }
    
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// ============================================
// RVC Conversion Endpoint (Inference)
// ============================================
app.post('/api/convert', async (req, res) => {
  try {
    if (!COLAB_API_URL) {
      return res.status(500).json({
        success: false,
        error: 'Server configuration error: COLAB_API_URL not set'
      });
    }

    const { audio_url, model_name, pitch, user_id } = req.body;

    if (!audio_url || !model_name) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: audio_url or model_name'
      });
    }

    console.log('🎵 Conversion request:', model_name);

    const response = await axios.post(`${COLAB_API_URL}/convert`, {
      audio_url, model_name, pitch, user_id
    }, {
      timeout: 120000, // 2 دقيقة
      headers: {
        'Content-Type': 'application/json'
      }
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

// ============================================
// Error Handling
// ============================================
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error'
  });
});

// ============================================
// Start Server
// ============================================
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log('=================================');
  console.log(`🚀 RVC Voice API Server running on port ${PORT}`);
  console.log(`🔗 URL: https://rvc-voice-api.onrender.com`);
  console.log(`📊 Health: https://rvc-voice-api.onrender.com/health`);
  console.log('=================================');
});
