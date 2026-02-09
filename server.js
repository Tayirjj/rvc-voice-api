app.post('/api/train', async (req, res) => {
  try {
    // استقبال جميع البيانات من Flutter
    const {
      exp_dir1, trainset_dir4, sr2, if_f0_3, spk_id5, np7,
      f0method8, save_epoch10, total_epoch11, batch_size12,
      if_save_latest13, pretrained_G14, pretrained_D15, gpus16,
      if_cache_gpu17, if_save_every_weights18, version19, gpus_rmvpe,
      user_id
    } = req.body;

    console.log('📥 RVC Training Request:');
    console.log('- Voice Name:', exp_dir1);
    console.log('- Audio URL:', trainset_dir4);
    console.log('- Sample Rate:', sr2);
    console.log('- Total Epochs:', total_epoch11);

    // إرسال إلى Colab
    const colabApiUrl = process.env.COLAB_API_URL || 'https://your-ngrok-url.ngrok-free.dev';
    
    const trainingResponse = await axios.post(`${colabApiUrl}/train`, {
      exp_dir1, trainset_dir4, sr2, if_f0_3, spk_id5, np7,
      f0method8, save_epoch10, total_epoch11, batch_size12,
      if_save_latest13, pretrained_G14, pretrained_D15, gpus16,
      if_cache_gpu17, if_save_every_weights18, version19, gpus_rmvpe,
      user_id
    }, {
      timeout: 600000 // 10 دقائق للتدريب الحقيقي
    });

    console.log('✅ Training completed:', trainingResponse.data);

    // حفظ النتيجة في Firestore
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
