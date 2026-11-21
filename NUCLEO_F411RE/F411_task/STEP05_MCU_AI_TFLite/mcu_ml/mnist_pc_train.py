# mnist_pc_train.py
# PC에서 MNIST 숫자 인식 모델 학습 (float32)

import tensorflow as tf
from tensorflow import keras
import numpy as np
import time
import os

# 1. MNIST 데이터 로드
print("[1/5] MNIST 데이터 로드 중...")
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()

# 정규화 (0~255 → 0~1)
x_train = x_train.astype(np.float32) / 255.0
x_test = x_test.astype(np.float32) / 255.0

# shape 확인
print(f"  학습 데이터: {x_train.shape}, 레이블: {y_train.shape}")
print(f"  테스트 데이터: {x_test.shape}, 레이블: {y_test.shape}")
print(f"  픽셀 범위: [{x_train.min()}, {x_train.max()}]")

# 2. 모델 정의
print("\n[2/5] 모델 정의 중...")
model = keras.Sequential([
    # 입력: 28x28 1채널 (Grayscale)
    keras.layers.InputLayer(input_shape=(28, 28, 1)),

    # Flatten: 28x28 → 784
    keras.layers.Flatten(),

    # 은닉층 1: 128 뉴런, ReLU 활성화
    keras.layers.Dense(128, activation='relu'),

    # 은닉층 2: 64 뉴런, ReLU 활성화
    keras.layers.Dense(64, activation='relu'),

    # 출력층: 10 뉴런 (0~9), Softmax
    keras.layers.Dense(10, activation='softmax')
])

model.summary()

# 3. 모델 컴파일
print("\n[3/5] 모델 컴파일 중...")
model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# 4. 모델 학습
print("\n[4/5] 모델 학습 시작...")

# EarlyStopping: 검증 손실이 3번 연속 개선 없으면 중단
callbacks = [
    keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True)
]

start_time = time.time()
history = model.fit(
    x_train, y_train,
    batch_size=64,
    epochs=20,
    validation_split=0.2,  # 학습 중 20%를 검증용으로 분할
    callbacks=callbacks,
    verbose=2
)
train_time = time.time() - start_time

print(f"\n✅ 학습 완료! 소요 시간: {train_time:.2f}초")

# 5. 모델 평가
print("\n[5/5] 테스트 세트 평가 중...")
test_loss, test_acc = model.evaluate(x_test, y_test, verbose=0)
print(f"\n📊 PC 모델 (float32) 테스트 정확도: {test_acc:.4f} ({test_acc * 100:.2f}%)")
print(f"   테스트 손실: {test_loss:.4f}")

# 6. 모델 저장
model.save('mnist_pc_model.h5')
print("\n💾 모델 저장 완료: mnist_pc_model.h5")