# unzip.py
import os
import numpy as np
from PIL import Image

# mnist.npz 위치
npz_path = r"C:\Users\user\.keras\datasets\mnist.npz"

# 저장할 폴더
output_dir = r"C:\Users\user\Desktop\MNIST_Images"

# 데이터 읽기
data = np.load(npz_path)

x_train = data["x_train"]
y_train = data["y_train"]

x_test = data["x_test"]
y_test = data["y_test"]


def save_dataset(images, labels, dataset_name):
    base = os.path.join(output_dir, dataset_name)

    # 숫자별 폴더 생성
    for i in range(10):
        os.makedirs(os.path.join(base, str(i)), exist_ok=True)

    # 이미지 저장
    for idx, (img, label) in enumerate(zip(images, labels)):
        filename = os.path.join(
            base,
            str(label),
            f"{idx:06d}.png"
        )

        Image.fromarray(img).save(filename)

    print(f"{dataset_name} 저장 완료 ({len(images)}장)")


save_dataset(x_train, y_train, "train")
save_dataset(x_test, y_test, "test")

print("모든 이미지 저장 완료!")
print("저장 위치:", output_dir)