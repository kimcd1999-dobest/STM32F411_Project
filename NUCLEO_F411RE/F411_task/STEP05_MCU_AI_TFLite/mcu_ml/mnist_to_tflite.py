# mnist_to_tflite.py
# PC 모델 → TFLite 변환 및 양자화

import tensorflow as tf
import numpy as np
import os

# 1. 저장된 PC 모델 로드
print("[1/6] PC 모델 로드 중...")
model = tf.keras.models.load_model('mnist_pc_model.h5')
print(f"  로드 완료: mnist_pc_model.h5")

# 2. MNIST 테스트 데이터 로드 (양자화 Calibration용)
print("\n[2/6] Calibration 데이터 로드 중...")
(_, _), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
x_test = x_test.astype(np.float32) / 255.0

# 대표 데이터셋 (100장만 사용)
calibration_data = x_test[:100]
print(f"  Calibration 데이터: {calibration_data.shape}")

# 3. Float32 TFLite 변환 (양자화 없음)
print("\n[3/6] Float32 TFLite 변환 중...")
converter_float = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_float_model = converter_float.convert()

float_path = 'mnist_float32.tflite'
with open(float_path, 'wb') as f:
    f.write(tflite_float_model)
float_size = os.path.getsize(float_path)
print(f"  ✅ Float32 TFLite 저장 완료: {float_path}")
print(f"     크기: {float_size:,} bytes ({float_size/1024:.1f} KB)")

# 4. Int8 양자화 TFLite 변환 (MCU용)
print("\n[4/6] Int8 양자화 TFLite 변환 중...")

def representative_dataset():
    """Calibration용 대표 데이터셋: 100장"""
    for i in range(100):
        # Shape: (1, 28, 28, 1)
        x = calibration_data[i].reshape(1, 28, 28, 1)
        yield [x.astype(np.float32)]

converter_int8 = tf.lite.TFLiteConverter.from_keras_model(model)
converter_int8.optimizations = [tf.lite.Optimize.DEFAULT]
converter_int8.representative_dataset = representative_dataset
# int8 연산으로 강제 지정 (일부 연산이 float32로 남는 것 방지)
converter_int8.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
# 입력/출력 타입을 int8로
converter_int8.inference_input_type = tf.int8
converter_int8.inference_output_type = tf.int8

tflite_int8_model = converter_int8.convert()

int8_path = 'mnist_int8_quantized.tflite'
with open(int8_path, 'wb') as f:
    f.write(tflite_int8_model)
int8_size = os.path.getsize(int8_path)
print(f"  ✅ Int8 양자화 TFLite 저장 완료: {int8_path}")
print(f"     크기: {int8_size:,} bytes ({int8_size/1024:.1f} KB)")

# 5. 크기 비교
print("\n[5/6] 모델 크기 비교")
reduction = (1 - int8_size / float_size) * 100
print(f"  Float32 모델: {float_size:>8,} bytes ({float_size/1024:.1f} KB)")
print(f"  Int8 양자화 모델: {int8_size:>8,} bytes ({int8_size/1024:.1f} KB)")
print(f"  📉 크기 감소율: {reduction:.1f}%")

# 6. 모델 정보 출력
print("\n[6/6] 모델 상세 정보")
# Float32 모델
interpreter_float = tf.lite.Interpreter(model_content=tflite_float_model)
interpreter_float.allocate_tensors()
float_details = interpreter_float.get_input_details()[0]

print(f"\n  [Float32 모델]")
print(f"    입력 shape: {float_details['shape']}")
print(f"    입력 dtype: {float_details['dtype']}")

# Int8 모델
interpreter_int8 = tf.lite.Interpreter(model_content=tflite_int8_model)
interpreter_int8.allocate_tensors()
int8_details = interpreter_int8.get_input_details()[0]

print(f"\n  [Int8 양자화 모델]")
print(f"    입력 shape: {int8_details['shape']}")
print(f"    입력 dtype: {int8_details['dtype']}")
print(f"    입력 scale: {int8_details['quantization_parameters']['scales']}")
print(f"    입력 zero_point: {int8_details['quantization_parameters']['zero_points']}")

print(f"\n{'='*50}")
print(f"✨ Int8 양자화 모델이 MCU(ESP32)에 탑재 가능한 크기로 줄었습니다!")
print(f"{'='*50}")