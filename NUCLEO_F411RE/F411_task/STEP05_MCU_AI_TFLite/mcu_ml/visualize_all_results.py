# visualize_all_results.py
# Visual Comparison: PC Keras vs Float32 TFLite vs Int8 TFLite

import tensorflow as tf
from tensorflow import keras
import numpy as np
import time
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

# Set default font parameter to prevent minus sign issues
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. Prepare Data and Models
# ============================================================
print("[1/7] Loading data and models...")
(_, _), (x_test, y_test) = keras.datasets.mnist.load_data()
x_test_f = x_test.astype(np.float32) / 255.0

# PC Keras Model (Re-training)
model = keras.Sequential([
    keras.layers.InputLayer(input_shape=(28, 28, 1)),
    keras.layers.Flatten(),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dense(64, activation='relu'),
    keras.layers.Dense(10, activation='softmax')
])
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
(x_train, y_train), _ = keras.datasets.mnist.load_data()
model.fit(x_train.astype(np.float32)/255.0, y_train, batch_size=64, epochs=5, verbose=0)

# TFLite Models
interp_f32 = tf.lite.Interpreter(model_path='mnist_float32.tflite')
interp_f32.allocate_tensors()
in_f32 = interp_f32.get_input_details()[0]
out_f32 = interp_f32.get_output_details()[0]

interp_i8 = tf.lite.Interpreter(model_path='mnist_int8_quantized.tflite')
interp_i8.allocate_tensors()
in_i8 = interp_i8.get_input_details()[0]
out_i8 = interp_i8.get_output_details()[0]

scale_i8 = in_i8['quantization_parameters']['scales'][0]
zp_i8 = in_i8['quantization_parameters']['zero_points'][0]

# ============================================================
# 2. Run Inference on 10,000 Test Images
# ============================================================
print("[2/7] Running inference on 10,000 images across 3 models...")

pred_pc = []
pred_f32 = []
pred_i8 = []

for i in range(10000):
    # PC Keras
    p = model.predict(x_test_f[i].reshape(1, 28, 28, 1), verbose=0)
    pred_pc.append(np.argmax(p[0]))

    # Float32 TFLite
    interp_f32.set_tensor(in_f32['index'], x_test_f[i].reshape(1, 28, 28, 1).astype(np.float32))
    interp_f32.invoke()
    pred_f32.append(np.argmax(interp_f32.get_tensor(out_f32['index'])[0]))

    # Int8 TFLite
    in_data = (x_test_f[i].reshape(1, 28, 28, 1) / scale_i8 + zp_i8).astype(np.int8)
    interp_i8.set_tensor(in_i8['index'], in_data)
    interp_i8.invoke()
    pred_i8.append(np.argmax(interp_i8.get_tensor(out_i8['index'])[0]))

    if (i + 1) % 2000 == 0:
        print(f"    {i + 1}/10000 completed")

pred_pc = np.array(pred_pc)
pred_f32 = np.array(pred_f32)
pred_i8 = np.array(pred_i8)

# ============================================================
# 3. [Visualization 1] Side-by-Side Prediction Comparison
# ============================================================
print("[3/7] Generating side-by-side comparison image...")

# Prioritize misclassified cases
wrong_i8 = np.where(pred_i8 != y_test)[0]
wrong_pc = np.where(pred_pc != y_test)[0]
wrong_f32 = np.where(pred_f32 != y_test)[0]
# Cases where only Int8 failed
only_i8_wrong = sorted(set(wrong_i8) - set(wrong_f32))

n_samples = 6  # Number of cases to display
if len(only_i8_wrong) >= n_samples:
    indices = only_i8_wrong[:n_samples]
else:
    indices = wrong_i8[:n_samples]

fig, axes = plt.subplots(n_samples, 4, figsize=(14, 3 * n_samples))
fig.suptitle('Prediction Comparison: PC Keras vs Float32 TFLite vs Int8 TFLite', fontsize=16, y=1.02)

for row, idx in enumerate(indices):
    img = x_test[idx]
    true_label = y_test[idx]

    for col, (name, pred) in enumerate([
        ('PC Keras (Float32)', pred_pc[idx]),
        ('TFLite Float32', pred_f32[idx]),
        ('TFLite Int8 (MCU)', pred_i8[idx])
    ]):
        ax = axes[row, col] if n_samples > 1 else axes[col]
        ax.imshow(img, cmap='gray')
        color = 'green' if pred == true_label else 'red'
        ax.set_title(f'{name}\nTrue: {true_label} / Pred: {pred}', color=color, fontsize=10)
        ax.axis('off')

    # Display Ground Truth Label
    ax = axes[row, 3] if n_samples > 1 else axes[3]
    ax.text(0.5, 0.5, f'{true_label}', fontsize=72, ha='center', va='center')
    ax.set_title('Ground Truth', fontsize=10)
    ax.axis('off')

plt.tight_layout()
plt.savefig('viz_side_by_side.png', dpi=150, bbox_inches='tight')
plt.close()
print("    ✅ Saved: viz_side_by_side.png")

# ============================================================
# 4. [Visualization 2] Confusion Matrix
# ============================================================
print("[4/7] Generating confusion matrix image...")

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Confusion Matrix by Model', fontsize=16)

for ax, (name, preds) in zip(axes, [
    ('PC Keras (Float32)', pred_pc),
    ('TFLite Float32', pred_f32),
    ('TFLite Int8 (MCU)', pred_i8)
]):
    cm = confusion_matrix(y_test, preds, labels=range(10))
    disp = ConfusionMatrixDisplay(cm, display_labels=range(10))
    disp.plot(ax=ax, cmap='Blues', colorbar=False, values_format='d')
    ax.set_title(name, fontsize=12)

plt.tight_layout()
plt.savefig('viz_confusion_matrix.png', dpi=150, bbox_inches='tight')
plt.close()
print("    ✅ Saved: viz_confusion_matrix.png")

# ============================================================
# 5. [Visualization 3] Error Pattern Analysis
# ============================================================
print("[5/7] Generating error analysis image...")

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Error Analysis (Misclassification Rate per Digit)', fontsize=16)

for ax, (name, preds) in zip(axes, [
    ('PC Keras (Float32)', pred_pc),
    ('TFLite Float32', pred_f32),
    ('TFLite Int8 (MCU)', pred_i8)
]):
    # Calculate error rate per digit
    error_rates = []
    for digit in range(10):
        mask = (y_test == digit)
        total = np.sum(mask)
        errors = np.sum(preds[mask] != digit) if total > 0 else 0
        error_rates.append(errors / total * 100)

    bars = ax.bar(range(10), error_rates, color='coral', edgecolor='white')
    # Highlight the highest error rate
    max_idx = np.argmax(error_rates)
    bars[max_idx].set_color('red')

    for i, v in enumerate(error_rates):
        ax.text(i, v + 0.3, f'{v:.1f}%', ha='center', fontsize=9)

    ax.set_xlabel('Digit Class')
    ax.set_ylabel('Error Rate (%)')
    ax.set_title(name)
    ax.set_xticks(range(10))
    ax.set_ylim(0, max(error_rates) + 5)

plt.tight_layout()
plt.savefig('viz_error_analysis.png', dpi=150, bbox_inches='tight')
plt.close()
print("    ✅ Saved: viz_error_analysis.png")

# ============================================================
# 6. [Visualization 4] Overall Performance Comparison
# ============================================================
print("[6/7] Generating performance benchmark charts...")

# Measure inference time (1,000 samples)
times = {'PC Keras': [], 'TFLite Float32': [], 'TFLite Int8': []}
for i in range(1000):
    t0 = time.perf_counter()
    model.predict(x_test_f[i].reshape(1, 28, 28, 1), verbose=0)
    times['PC Keras'].append(time.perf_counter() - t0)

    t0 = time.perf_counter()
    interp_f32.set_tensor(in_f32['index'], x_test_f[i].reshape(1, 28, 28, 1).astype(np.float32))
    interp_f32.invoke()
    _ = interp_f32.get_tensor(out_f32['index'])
    times['TFLite Float32'].append(time.perf_counter() - t0)

    t0 = time.perf_counter()
    in_data = (x_test_f[i].reshape(1, 28, 28, 1) / scale_i8 + zp_i8).astype(np.int8)
    interp_i8.set_tensor(in_i8['index'], in_data)
    interp_i8.invoke()
    _ = interp_i8.get_tensor(out_i8['index'])
    times['TFLite Int8'].append(time.perf_counter() - t0)

# Calculate model sizes
pc_size = sum(w.nbytes for w in model.get_weights())
f32_size = len(open('mnist_float32.tflite', 'rb').read())
i8_size = len(open('mnist_int8_quantized.tflite', 'rb').read())

# Calculate accuracy
acc_pc = np.mean(pred_pc == y_test) * 100
acc_f32 = np.mean(pred_f32 == y_test) * 100
acc_i8 = np.mean(pred_i8 == y_test) * 100

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Model Performance & Efficiency Comparison', fontsize=16)

labels = ['PC Keras\n(Float32)', 'TFLite\nFloat32', 'TFLite Int8\n(MCU)']
colors = ['#4CAF50', '#2196F3', '#FF9800']

# (a) Model Size
ax = axes[0]
bars = ax.bar(labels, [pc_size/1024, f32_size/1024, i8_size/1024], color=colors, edgecolor='white')
for bar, val in zip(bars, [pc_size/1024, f32_size/1024, i8_size/1024]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
            f'{val:.1f} KB', ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('Size (KB)')
ax.set_title('Model Size', fontsize=13)
ax.set_ylim(0, max(pc_size/1024, f32_size/1024, i8_size/1024) * 1.3)

# (b) Test Accuracy
ax = axes[1]
bars = ax.bar(labels, [acc_pc, acc_f32, acc_i8], color=colors, edgecolor='white')
for bar, val in zip(bars, [acc_pc, acc_f32, acc_i8]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{val:.2f}%', ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('Accuracy (%)')
ax.set_title('Test Accuracy', fontsize=13)
ax.set_ylim(90, 100)

# (c) Inference Time
ax = axes[2]
avg_times = [np.mean(times['PC Keras']) * 1000,
             np.mean(times['TFLite Float32']) * 1000,
             np.mean(times['TFLite Int8']) * 1000]
bars = ax.bar(labels, avg_times, color=colors, edgecolor='white')
for bar, val in zip(bars, avg_times):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
            f'{val:.3f} ms', ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('Latency (ms)')
ax.set_title('Avg. Inference Time (per image)', fontsize=13)
ax.set_ylim(0, max(avg_times) * 1.3)

plt.tight_layout()
plt.savefig('viz_speed_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("    ✅ Saved: viz_speed_comparison.png")

# ============================================================
# 7. Summary Report
# ============================================================
print(f"\n{'='*60}")
print(f"{'📊 Benchmark Summary Report':^58}")
print(f"{'='*60}")
print(f"  {'Metric':<20} {'PC Keras':<15} {'TFLite F32':<15} {'TFLite Int8':<15}")
print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")
print(f"  {'Model Size':<20} {pc_size/1024:<15.1f} {f32_size/1024:<15.1f} {i8_size/1024:<15.1f} KB")
print(f"  {'Accuracy':<20} {acc_pc:<15.2f} {acc_f32:<15.2f} {acc_i8:<15.2f} %")
print(f"  {'Inference Time':<20} {avg_times[0]:<15.3f} {avg_times[1]:<15.3f} {avg_times[2]:<15.3f} ms")
print(f"{'='*60}")
print(f"\n✅ Output Files Saved:")
print(f"  1. viz_side_by_side.png     - Side-by-side prediction comparisons")
print(f"  2. viz_confusion_matrix.png - Confusion matrices across models")
print(f"  3. viz_error_analysis.png   - Misclassification rate per digit")
print(f"  4. viz_speed_comparison.png - Benchmark charts (Size, Accuracy, Latency)")

# Quantization Impact Analysis
print(f"\n📌 Quantization Impact Analysis:")
common_correct = np.sum((pred_f32 == y_test) & (pred_i8 == y_test))
f32_only_correct = np.sum((pred_f32 == y_test) & (pred_i8 != y_test))
i8_only_correct = np.sum((pred_f32 != y_test) & (pred_i8 == y_test))
both_wrong = np.sum((pred_f32 != y_test) & (pred_i8 != y_test))

print(f"  Both correct: {common_correct} images ({common_correct/100:.1f}%)")
print(f"  Float32 only correct (Quantization Loss): {f32_only_correct} images ({f32_only_correct/100:.1f}%)")
print(f"  Int8 only correct (Quantization Gain): {i8_only_correct} images ({i8_only_correct/100:.1f}%)")
print(f"  Both wrong: {both_wrong} images ({both_wrong/100:.1f}%)")