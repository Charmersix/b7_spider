import json
import os
import urllib.request
import urllib.error

def fetch_and_download(activity_id, base_folder="jjt_images"):
    # 1. 创建统一的主图库文件夹
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
        print(f"📁 已创建主图库文件夹: {base_folder}")
        
    # 2. 准备请求 URL、数据和请求头
    url = "https://mng.jjt.org.cn/api/vote/get_users"
    
    # 动态传入请求包里的 id
    payload = {
        "id": str(activity_id),
        "keyword": "",
        "page": 1,
        "limit": 1000
    }
    post_data = json.dumps(payload).encode('utf-8')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "http://h5.jjt.org.cn",
        "Referer": "http://h5.jjt.org.cn/",
        "Accept": "*/*"
    }

    print(f"\n🚀 [活动 {activity_id}] 正在向接口发送请求，获取数据...")
    
    # 3. 发送 POST 请求获取 JSON 数据
    try:
        req = urllib.request.Request(url, data=post_data, headers=headers)
        with urllib.request.urlopen(req) as response:
            response_text = response.read().decode('utf-8')
            parsed_data = json.loads(response_text)
            print(f"✅ [活动 {activity_id}] 成功获取接口数据！\n")
    except urllib.error.URLError as e:
        print(f"❌ [活动 {activity_id}] 请求接口失败: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ [活动 {activity_id}] 解析返回的 JSON 数据失败: {e}")
        return

    # 4. 解析用户列表并开始下载
    user_list = parsed_data.get("data", {}).get("data", [])
    if not user_list:
        print(f"⚠️ [活动 {activity_id}] 接口返回成功，但没有找到用户数据。")
        return
    
    total_downloaded = 0
    
    for user in user_list:
        user_name = user.get("name", "未知昵称")
        phone = user.get("phone")
        images = user.get("images", [])
        
        # 清理昵称中的特殊字符，防止 Windows 建文件夹报错
        safe_name = "".join(c for c in str(user_name) if c not in r'\/:*?"<>|')
        safe_phone = str(phone) if phone else "无手机号"
            
        # 💡 组装文件夹名称 "昵称_手机号"，直接丢到主文件夹下
        folder_name = f"{safe_name}_{safe_phone}"
        user_folder = os.path.join(base_folder, folder_name)
        
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        
        print(f"[{activity_id}] 开始处理: {safe_name} - 共 {len(images)} 张...")
        
        for img_url in images:
            if not img_url:
                continue
                
            # 去掉 URL 中的缩略图参数，获取高清原图
            clean_url = img_url.split('?')[0]
            original_filename = clean_url.split('/')[-1]
            save_path = os.path.join(user_folder, original_filename)
            
            # 断点续传：已存在则跳过
            if os.path.exists(save_path):
                print(f"  ⏭️ 已存在，跳过: {original_filename}")
                continue
            
            try:
                # 请求图片
                img_req = urllib.request.Request(clean_url, headers={'User-Agent': headers['User-Agent']})
                with urllib.request.urlopen(img_req) as img_res, open(save_path, 'wb') as out_file:
                    out_file.write(img_res.read())
                print(f"  ✅ 成功下载: {original_filename}")
                total_downloaded += 1
            except Exception as e:
                print(f"  ❌ 下载失败 [{clean_url}]: {e}")
                
    print(f"\n🎉 [活动 {activity_id}] 提取完毕！本次下载了 {total_downloaded} 张新图片。")

if __name__ == "__main__":
    # 💡 包含你要求的所有 ID
    target_ids = ["21", "27", "28"]
    
    print("🤖 爬虫任务启动...")
    for act_id in target_ids:
        fetch_and_download(act_id)
        
    print("\n🏁 所有活动的图片已全部下载并合并完毕！")