#! /usr/bin/env python
# coding=utf-8
#================================================================
#   Copyright (C) 2019 * Ltd. All rights reserved.
#
#   Editor      : VIM
#   File name   : train.py
#   Author      : YunYang1994
#   Created date: 2019-10-14 19:12:36
#   Description :
#
#================================================================

import os
import cv2
import random
import tensorflow as tf
import numpy as np
from fcn8s import FCN8s
from PIL import Image
from config import colormap, classes, rgb_mean, rgb_std


def create_image_label_path_generator(images_filepath, labels_filepath):
    image_paths = open(images_filepath).readlines()
    all_label_txts = os.listdir(labels_filepath)
    image_label_paths = []
    for label_txt in all_label_txts:
        label_name = label_txt[:-4]
        label_path = labels_filepath + "/" + label_txt
        for image_path in image_paths:
            image_path = image_path.rstrip()
            image_name = image_path.split("/")[-1][:-4]
            if label_name == image_name:
                image_label_paths.append((image_path, label_path))
    while True:
        random.shuffle(image_label_paths)
        for i in range(len(image_label_paths)):
            yield image_label_paths[i]


def process_image_label(image_path, label_path):
    # image = misc.imread(image_path)
    image = cv2.imread(image_path)
    image = cv2.resize(image, (224, 224), interpolation=cv2.INTER_NEAREST)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # data augmentation here
    # pass
    # image transformation here
    image = (image / 255. - rgb_mean) / rgb_std

    label = open(label_path).readlines()
    label = [np.array(line.rstrip().split(" ")) for line in label]
    label = np.array(label, dtype=np.int)
    label = cv2.resize(label, (224, 224), interpolation=cv2.INTER_NEAREST)
    label = label.astype(np.int)

    return image, label


def DataGenerator(train_image_txt, train_labels_dir, batch_size):
    """
    generate image and mask at the same time
    """
    image_label_path_generator = create_image_label_path_generator(
        train_image_txt, train_labels_dir
    )
    while True:
        images = np.zeros(shape=[batch_size, 224, 224, 3])
        labels = np.zeros(shape=[batch_size, 224, 224], dtype=np.float)
        for i in range(batch_size):
            image_path, label_path = next(image_label_path_generator)
            image, label = process_image_label(image_path, label_path)
            images[i], labels[i] = image, label
        yield images, labels


def visual_result(image, label, alpha=0.7):
    """
    image shape -> [H, W, C]
    label shape -> [H, W]
    """
    image = (image * rgb_std + rgb_mean) * 255
    image, label = image.astype(np.int), label.astype(np.int)
    H, W, C = image.shape
    masks_color = np.zeros(shape=[H, W, C])
    inv_masks_color = np.zeros(shape=[H, W, C])
    cls = []
    for i in range(H):
        for j in range(W):
            cls_idx = label[i, j]
            masks_color[i, j] = np.array(colormap[cls_idx])
            cls.append(cls_idx)
            if classes[cls_idx] == "background":
                inv_masks_color[i, j] = alpha * image[i, j]

    show_image = np.zeros(shape=[224, 672, 3])
    cls = set(cls)
    for x in cls:
        print("=> ", classes[x])
    show_image[:, :224, :] = image
    show_image[:, 224:448, :] = masks_color
    show_image[:, 448:, :] = (1-alpha)*image + alpha*masks_color + inv_masks_color
    show_image = Image.fromarray(np.uint8(show_image))
    return show_image

TrainSet = DataGenerator("./data/train_image.txt", "./data/train_labels", 2)
TestSet  = DataGenerator("./data/test_image.txt", "./data/test_labels", 1)

model = FCN8s(n_class=21)
callback = tf.keras.callbacks.ModelCheckpoint("model.h5", verbose=1, save_weights_only=True)
model.compile(optimizer=tf.keras.optimizers.Adam(lr=1e-4),
              callback=callback,
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

## train your FCN8s model
model.fit_generator(TrainSet, steps_per_epoch=6000, epochs=30)
model.save_weights("model.h5")

## load weights and test your model after training
## if you want to test model, first you need to initialize your model
## with "model(data)", and then load model weights

# data = np.ones(shape=[1,224,224,3], dtype=np.float)
# model(data)
# model.load_weights("model.h5")

for idx, (x, y) in enumerate(TestSet):
    result = model(x)
    pred_label = tf.argmax(result, axis=-1)
    result = visual_result(x[0], pred_label[0].numpy())
    save_file = "./data/prediction/%d.jpg" %idx
    print("=> saving prediction result into ", save_file)
    result.save(save_file)
    if idx == 209:
        result.show()
        break



