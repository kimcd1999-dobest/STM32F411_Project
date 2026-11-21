# mnist_tflite_eval.py
# TFLite 모델 (Float32 vs Int8) 추론 및 정확도/속도 비교

import tensorflow as tf
import numpy as np
import time

# 1. MNIST 테스트 데이터 로드
print("[1/7] MNIST 테스트 데이터 로드 중...")
(_, _), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
x_test_float = x_test.astype(np.float32) / 255.0  # [0, 1]
print(f"  테스트 데이터: {x_test.shape}")

# 2. TFLite 모델 로드
print("\n[2/7] TFLite 모델 로드 중...")

# Float32 모델
interpreter_float = tf.lite.Interpreter(model_path='mnist_float32.tflite')
interpreter_float.allocate_tensors()
input_float = interpreter_float.get_input_details()[0]
output_float = interpreter_float.get_output_details()[0]
print(f"  Float32 모델 로드 완료")
print(f"    입력: {input_float['shape']}, {input_float['dtype']}")
print(f"    출력: {output_float['shape']}, {output_float['dtype']}")

# Int8 모델
interpreter_int8 = tf.lite.Interpreter(model_path='mnist_int8_quantized.tflite')
interpreter_int8.allocate_tensors()
input_int8 = interpreter_int8.get_input_details()[0]
output_int8 = interpreter_int8.get_output_details()[0]
print(f"  Int8 양자화 모델 로드 완료")
print(f"    입력: {input_int8['shape']}, {input_int8['dtype']}")
print(f"    출력: {output_int8['shape']}, {output_int8['dtype']}")

# 3. Float32 모델 추론
print("\n[3/7] Float32 모델 추론 중...")

correct_float = 0
times_float = []

for i in range(len(x_test)):
    # 입력 전처리
    input_data = x_test_float[i].reshape(1, 28, 28, 1).astype(np.float32)

    # 추론
    start = time.perf_counter()
    interpreter_float.set_tensor(input_float['index'], input_data)
    interpreter_float.invoke()
    output_data = interpreter_float.get_tensor(output_float['index'])
    elapsed = time.perf_counter() - start

    # 예측
    prediction = np.argmax(output_data[0])
    if prediction == y_test[i]:
        correct_float += 1
    times_float.append(elapsed)

    if (i + 1) % 2000 == 0:
        print(f"    Float32: {i + 1}/10000 완료 (현재 정확도: {correct_float / (i + 1):.4f})")

accuracy_float = correct_float / len(x_test)
avg_time_float = np.mean(times_float) * 1000  # ms
print(f"\n  ✅ Float32 TFLite 정확도: {accuracy_float:.4f} ({accuracy_float * 100:.2f}%)")
print(f"     평균 추론 시간: {avg_time_float:.4f} ms")

# 4. Int8 양자화 모델 추론
print("\n[4/7] Int8 양자화 모델 추론 중...")

correct_int8 = 0
times_int8 = []

for i in range(len(x_test)):
    # Int8 입력 변환
    # float32 [0, 1] → int8 [-128, 127]
    input_scale = input_int8['quantization_parameters']['scales'][0]
    input_zero_point = input_int8['quantization_parameters']['zero_points'][0]
    input_data_float = x_test_float[i].reshape(1, 28, 28, 1)
    input_data_int8 = (input_data_float / input_scale + input_zero_point).astype(np.int8)

    # 추론
    start = time.perf_counter()
    interpreter_int8.set_tensor(input_int8['index'], input_data_int8)
    interpreter_int8.invoke()
    output_data = interpreter_int8.get_tensor(output_int8['index'])
    elapsed = time.perf_counter() - start

    # 예측
    prediction = np.argmax(output_data[0])
    if prediction == y_test[i]:
        correct_int8 += 1
    times_int8.append(elapsed)

    if (i + 1) % 2000 == 0:
        print(f"    Int8: {i + 1}/10000 완료 (현재 정확도: {correct_int8 / (i + 1):.4f})")

accuracy_int8 = correct_int8 / len(x_test)
avg_time_int8 = np.mean(times_int8) * 1000  # ms
print(f"\n  ✅ Int8 양자화 TFLite 정확도: {accuracy_int8:.4f} ({accuracy_int8 * 100:.2f}%)")
print(f"     평균 추론 시간: {avg_time_int8:.4f} ms")

# 5. 오분류 사례 분석
print("\n[5/7] 오분류 사례 분석 중...")

misclassified_float = []
misclassified_int8 = []

for i in range(len(x_test)):
    # Float32
    input_data = x_test_float[i].reshape(1, 28, 28, 1).astype(np.float32)
    interpreter_float.set_tensor(input_float['index'], input_data)
    interpreter_float.invoke()
    pred_float = np.argmax(interpreter_float.get_tensor(output_float['index'])[0])

    # Int8
    input_data_int8 = (x_test_float[i].reshape(1, 28, 28, 1) / input_scale + input_zero_point).astype(np.int8)
    interpreter_int8.set_tensor(input_int8['index'], input_data_int8)
    interpreter_int8.invoke()
    pred_int8 = np.argmax(interpreter_int8.get_tensor(output_int8['index'])[0])

    if pred_float != y_test[i]:
        misclassified_float.append((i, y_test[i], pred_float))
    if pred_int8 != y_test[i]:
        misclassified_int8.append((i, y_test[i], pred_int8))

print(f"  Float32 오분류: {len(misclassified_float)}개 / 10000")
print(f"  Int8 오분류: {len(misclassified_int8)}개 / 10000")

# 양자화로 인해 추가로 오분류된 사례 (Int8만 틀린 경우)
only_int8_wrong = [m for m in misclassified_int8 if m not in misclassified_float]
print(f"  양자화로 인한 추가 오분류: {len(only_int8_wrong)}개")

if len(only_int8_wrong) > 0:
    print(f"\n  🔍 양자화로 추가 오분류된 예 (최대 5개):")
    for idx, true_label, pred_label in only_int8_wrong[:5]:
        print(f"    - 테스트 #{idx}: 실제={true_label}, 예측={pred_label}")

# 6. 추론 시간 분포 분석
print(f"\n[6/7] 추론 시간 분포")
print(f"  Float32:")
print(f"    최소: {np.min(times_float) * 1000:.4f} ms")
print(f"    최대: {np.max(times_float) * 1000:.4f} ms")
print(f"    평균: {avg_time_float:.4f} ms")
print(f"    중앙값: {np.median(times_float) * 1000:.4f} ms")
print(f"    표준편차: {np.std(times_float) * 1000:.4f} ms")
print(f"  Int8:")
print(f"    최소: {np.min(times_int8) * 1000:.4f} ms")
print(f"    최대: {np.max(times_int8) * 1000:.4f} ms")
print(f"    평균: {avg_time_int8:.4f} ms")
print(f"    중앙값: {np.median(times_int8) * 1000:.4f} ms")
print(f"    표준편차: {np.std(times_int8) * 1000:.4f} ms")

# 7. 종합 결과 출력
print(f"\n{'='*60}")
print(f"📊 TFLite 모델 종합 평가 결과")
print(f"{'='*60}")
print(f"  {'항목':<25} {'Float32':<20} {'Int8 양자화':<20}")
print(f"  {'-'*25} {'-'*20} {'-'*20}")
print(f"  {'모델 크기':<25} {437544/1024:<10.1f} KB     {109384/1024:<10.1f} KB")
print(f"  {'정확도':<25} {accuracy_float:<10.4f}     {accuracy_int8:<10.4f}")
print(f"  {'평균 추론 시간':<25} {avg_time_float:<10.2f} ms     {avg_time_int8:<10.2f} ms")
print(f"  {'오분류 개수':<25} {len(misclassified_float):<10}     {len(misclassified_int8):<10}")
print(f"{'='*60}")