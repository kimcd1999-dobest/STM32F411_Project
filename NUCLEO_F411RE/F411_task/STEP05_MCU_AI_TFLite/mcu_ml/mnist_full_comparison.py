# mnist_full_comparison.py
# 전체 파이프라인: 학습 → 변환 → 평가 → 비교

import tensorflow as tf
from tensorflow import keras
import numpy as np
import time
import os

print("=" * 60)
print("🧪 MNIST 전체 비교 실험")
print("=" * 60)

# ─── 1. 데이터 로드 ─────────────────────────────────
print("\n[1] MNIST 데이터 로드")
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
x_train = x_train.astype(np.float32) / 255.0
x_test_f = x_test.astype(np.float32) / 255.0
print(f"    학습: {x_train.shape}, 테스트: {x_test_f.shape}")

# ─── 2. PC 모델 학습 ────────────────────────────────
print("\n[2] PC 모델 학습 (float32)")
model = keras.Sequential([
    keras.layers.InputLayer(input_shape=(28, 28, 1)),
    keras.layers.Flatten(),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dense(64, activation='relu'),
    keras.layers.Dense(10, activation='softmax')
])
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

t0 = time.time()
model.fit(x_train, y_train, batch_size=64, epochs=10, validation_split=0.2, verbose=0)
train_time = time.time() - t0

pc_loss, pc_acc = model.evaluate(x_test_f, y_test, verbose=0)
pc_size = 0
for w in model.get_weights():
    pc_size += w.nbytes
print(f"    학습 시간: {train_time:.1f}초")
print(f"    정확도: {pc_acc:.4f}")
print(f"    파라미터 크기: {pc_size:,} bytes ({pc_size/1024:.1f} KB)")

# ─── 3. TFLite 변환 ─────────────────────────────────
print("\n[3] TFLite 변환")

# Float32
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_float = converter.convert()
float_size = len(tflite_float)
print(f"    Float32 TFLite: {float_size:,} bytes ({float_size/1024:.1f} KB)")

# Int8
def rep_dataset():
    for i in range(100):
        yield [x_test_f[i].reshape(1, 28, 28, 1)]
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = rep_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
tflite_int8 = converter.convert()
int8_size = len(tflite_int8)
print(f"    Int8 양자화 TFLite: {int8_size:,} bytes ({int8_size/1024:.1f} KB)")
print(f"    📉 압축률: {(1 - int8_size/float_size)*100:.1f}%")

# ─── 4. TFLite 평가 ─────────────────────────────────
print("\n[4] TFLite 모델 평가")

results = {}
for name, model_bytes, input_type in [
    ("Float32 TFLite", tflite_float, np.float32),
    ("Int8 TFLite", tflite_int8, np.int8)
]:
    interpreter = tf.lite.Interpreter(model_content=model_bytes)
    interpreter.allocate_tensors()
    in_d = interpreter.get_input_details()[0]
    out_d = interpreter.get_output_details()[0]

    correct = 0
    times_list = []
    for i in range(1000):  # 1000장만 측정 (속도)
        if input_type == np.int8:
            scale = in_d['quantization_parameters']['scales'][0]
            zp = in_d['quantization_parameters']['zero_points'][0]
            in_data = (x_test_f[i].reshape(1, 28, 28, 1) / scale + zp).astype(np.int8)
        else:
            in_data = x_test_f[i].reshape(1, 28, 28, 1).astype(np.float32)

        t0 = time.perf_counter()
        interpreter.set_tensor(in_d['index'], in_data)
        interpreter.invoke()
        out = interpreter.get_tensor(out_d['index'])
        elapsed = time.perf_counter() - t0

        if np.argmax(out[0]) == y_test[i]:
            correct += 1
        times_list.append(elapsed)

    # 전체 정확도 (10000장)
    correct_all = 0
    for i in range(10000):
        if input_type == np.int8:
            in_data = (x_test_f[i].reshape(1, 28, 28, 1) / scale + zp).astype(np.int8)
        else:
            in_data = x_test_f[i].reshape(1, 28, 28, 1).astype(np.float32)
        interpreter.set_tensor(in_d['index'], in_data)
        interpreter.invoke()
        if np.argmax(interpreter.get_tensor(out_d['index'])[0]) == y_test[i]:
            correct_all += 1

    results[name] = {
        'accuracy': correct_all / 10000,
        'avg_time_ms': np.mean(times_list) * 1000,
        'size_bytes': len(model_bytes)
    }
    print(f"    {name}: 정확도={results[name]['accuracy']:.4f}, "
          f"추론시간={results[name]['avg_time_ms']:.3f}ms")

# ─── 5. 결과 요약 ──────────────────────────────────
print(f"\n{'='*70}")
print(f"{'📊 최종 비교표':^68}")
print(f"{'='*70}")
print(f"{'모델':<25} {'크기(KB)':<12} {'정확도(%)':<12} {'추론시간(ms)':<15}")
print(f"{'-'*25} {'-'*12} {'-'*12} {'-'*15}")
print(f"{'PC Keras (float32)':<25} {pc_size/1024:<12.1f} {pc_acc*100:<12.2f} {'N/A':<15}")
print(f"{'TFLite Float32':<25} {float_size/1024:<12.1f} "
      f"{results['Float32 TFLite']['accuracy']*100:<12.2f} "
      f"{results['Float32 TFLite']['avg_time_ms']:<12.3f} ms")
print(f"{'TFLite Int8 (MCU용)':<25} {int8_size/1024:<12.1f} "
      f"{results['Int8 TFLite']['accuracy']*100:<12.2f} "
      f"{results['Int8 TFLite']['avg_time_ms']:<12.3f} ms")
print(f"{'='*70}")

# 속도 향상
speedup = results['Float32 TFLite']['avg_time_ms'] / results['Int8 TFLite']['avg_time_ms']
print(f"\n💡 인사이트")
print(f"   • Int8 모델은 Float32 대비 크기 {((1-int8_size/float_size)*100):.0f}% 감소")
print(f"   • 추론 속도 {speedup:.1f}배 향상")
print(f"   • 정확도 손실: {(results['Float32 TFLite']['accuracy'] - results['Int8 TFLite']['accuracy'])*100:.2f}%p")
print(f"   • MCU(ESP32)에 탑재 시 {int8_size/1024:.1f}KB면 충분 (ESP32 SRAM: ~320KB)")