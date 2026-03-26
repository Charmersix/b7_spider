import os
import shutil

# 设置源文件夹和目标文件夹
source_folder = 'jjt_images'
target_folder = 'collected_jjt_images'

# 支持的图片格式
image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')

if not os.path.exists(target_folder):
    os.makedirs(target_folder)

count = 0
# 递归遍历 jjt_images 及其所有子文件夹
for root, dirs, files in os.walk(source_folder):
    for file in files:
        if file.lower().endswith(image_exts):
            source_path = os.path.join(root, file)
            target_path = os.path.join(target_folder, file)
            
            # 处理文件名重复，防止覆盖
            base, ext = os.path.splitext(file)
            counter = 1
            while os.path.exists(target_path):
                target_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
                counter += 1
            
            shutil.copy2(source_path, target_path)
            count += 1

print(f"✅ 处理完成！共提取 {count} 张图片到目录: {target_folder}")