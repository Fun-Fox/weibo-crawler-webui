import streamlit as st
import json
import os
import subprocess
import zipfile
from pathlib import Path
import shutil

# 设置页面标题
st.set_page_config(page_title="微博爬虫管理界面", layout="wide")

# 页面标题
st.title("微博采样工具")

# 创建两个标签页
tab1, tab2 = st.tabs(["爬虫配置与执行", "素材管理"])


# 读取配置文件
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("未找到配置文件 config.json")
        return None
    except json.JSONDecodeError:
        st.error("配置文件格式错误")
        return None


# 保存配置文件
def save_config(config):
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"保存配置文件时出错: {e}")
        return False


# 在第一个标签页中
with tab1:
    st.header("爬虫配置与执行")

    # 加载配置
    config = load_config()
    if config is None:
        st.stop()

    # 用户ID列表配置
    st.subheader("用户ID配置")

    # 处理user_id_list，支持列表和字符串
    if isinstance(config['user_id_list'], list):
        user_ids_default = '\n'.join(config['user_id_list'])
    else:
        user_ids_default = config['user_id_list']

    user_ids = st.text_area(
        "请输入用户ID列表（每行一个ID）",
        value=user_ids_default,
        height=150,
        help="可以输入多个用户ID，每行一个，或输入文件路径"
    )

    # 其他配置选项
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("爬取范围设置")
        only_crawl_original = st.radio(
            "爬取微博类型",
            options=[0, 1],
            index=config['only_crawl_original'],
            format_func=lambda x: "全部微博（原创+转发）" if x == 0 else "仅原创微博"
        )

        # 处理since_date，支持整数和字符串
        if isinstance(config['since_date'], int):
            since_date_default = config['since_date']
        else:
            # 如果是日期字符串，提取日期部分
            if "T" in str(config['since_date']):
                since_date_default = config['since_date'].split("T")[0]
            else:
                since_date_default = config['since_date']

        since_date = st.date_input(
            "起始日期",
            value=st.session_state.get('since_date',
                                       since_date_default) if 'since_date' in st.session_state else since_date_default
        )

        # 将日期保存到session_state
        st.session_state.since_date = since_date

        st.subheader("文件保存设置")
        all_write_modes = ["csv"]
        write_modes = st.multiselect(
            "保存格式",
            options=all_write_modes,
            default=config['write_mode'] if isinstance(config['write_mode'], list) else [config['write_mode']],
            help="选择结果保存的格式"
        )
    with col2:
        st.subheader("评论和转发设置")
        download_comment = st.checkbox(
            "下载评论",
            value=bool(config.get('download_comment', 0)),
            help="下载微博的评论"
        )

        if download_comment:
            comment_max_download_count = st.number_input(
                "评论最大下载数",
                min_value=0,
                value=config.get('comment_max_download_count', 100),
                help="每条微博最多下载的评论数，0表示下载全部"
            )

        download_repost = st.checkbox(
            "下载转发",
            value=bool(config.get('download_repost', 0)),
            help="下载微博的转发"
        )

        if download_repost:
            repost_max_download_count = st.number_input(
                "转发最大下载数",
                min_value=0,
                value=config.get('repost_max_download_count', 100),
                help="每条微博最多下载的转发数，0表示下载全部"
            )

    with col3:
        st.subheader("媒体下载设置")
        original_pic_download = st.checkbox(
            "下载原创微博图片",
            value=bool(config['original_pic_download']),
            help="下载用户自己发布的微博中的图片"
        )

        retweet_pic_download = st.checkbox(
            "下载转发微博图片",
            value=bool(config['retweet_pic_download']),
            help="下载转发的微博中的图片"
        )

        original_video_download = st.checkbox(
            "下载原创微博视频",
            value=bool(config['original_video_download']),
            help="下载用户自己发布的微博中的视频"
        )

        retweet_video_download = st.checkbox(
            "下载转发微博视频",
            value=bool(config['retweet_video_download']),
            help="下载转发的微博中的视频"
        )

        # Live Photo下载设置
        if 'original_live_photo_download' in config:
            original_live_photo_download = st.checkbox(
                "下载原创微博Live Photo",
                value=bool(config['original_live_photo_download']),
                help="下载用户自己发布的微博中的Live Photo视频"
            )

        if 'retweet_live_photo_download' in config:
            retweet_live_photo_download = st.checkbox(
                "下载转发微博Live Photo",
                value=bool(config['retweet_live_photo_download']),
                help="下载转发的微博中的Live Photo视频"
            )

        st.subheader("Cookie设置")
        cookie = st.text_input(
            "Cookie（可选）",
            value=config['cookie'] if config['cookie'] != "your cookie" else "",
            type="password",
            help="登录微博账号的Cookie，可以突破一些限制"
        )

    # 更新配置
    if st.button("保存配置", type="primary"):
        # 处理用户ID列表
        if '\n' in user_ids:
            processed_user_ids = [uid.strip() for uid in user_ids.split('\n') if uid.strip()]
            # 如果只有一个ID且不是文件路径，也可以转换为字符串
            if len(processed_user_ids) == 1 and not processed_user_ids[0].endswith('.txt'):
                processed_user_ids = processed_user_ids
        else:
            processed_user_ids = [user_ids.strip()]

        # 更新配置
        config['user_id_list'] = processed_user_ids
        config['only_crawl_original'] = only_crawl_original
        config['since_date'] = str(since_date)
        config['write_mode'] = write_modes if write_modes else ["csv"]
        config['original_pic_download'] = int(original_pic_download)
        config['retweet_pic_download'] = int(retweet_pic_download)
        config['original_video_download'] = int(original_video_download)
        config['retweet_video_download'] = int(retweet_video_download)

        if 'original_live_photo_download' in config:
            config['original_live_photo_download'] = int(original_live_photo_download)
        if 'retweet_live_photo_download' in config:
            config['retweet_live_photo_download'] = int(retweet_live_photo_download)

        if 'download_comment' in config:
            config['download_comment'] = int(download_comment)
        if 'comment_max_download_count' in config and download_comment:
            config['comment_max_download_count'] = comment_max_download_count

        if 'download_repost' in config:
            config['download_repost'] = int(download_repost)
        if 'repost_max_download_count' in config and download_repost:
            config['repost_max_download_count'] = repost_max_download_count

        config['cookie'] = cookie if cookie else "your cookie"

        if save_config(config):
            st.success("配置已保存！")
        else:
            st.error("配置保存失败！")

    # 执行爬虫
    st.subheader("执行爬虫")

    # 检查weibo.py是否存在
    if not os.path.exists('weibo.py'):
        st.error("未找到 weibo.py 文件，请确认文件是否存在")
    else:
        if st.button("开始爬取", type="primary", use_container_width=True):
            with st.spinner("正在执行爬虫..."):
                try:
                    # 显示执行命令
                    st.info("执行命令: python weibo.py")

                    # 创建一个占位符来显示实时输出
                    output_placeholder = st.empty()
                    output_lines = []

                    # 使用subprocess.Popen来获取实时输出
                    process = subprocess.Popen(
                        ['python', 'weibo.py'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )

                    # 实时读取输出
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            output_lines.append(output)
                            # 限制显示的行数，避免界面卡顿
                            if len(output_lines) > 100:
                                output_lines = output_lines[-100:]
                            output_placeholder.text_area("实时日志", ''.join(output_lines), height=300)

                    # 获取返回码
                    return_code = process.poll()

                    if return_code == 0:
                        st.success("爬取完成！")
                    else:
                        st.error(f"爬取失败，返回码: {return_code}")

                except subprocess.TimeoutExpired:
                    st.error("爬取超时！")
                except FileNotFoundError:
                    st.error("未找到Python执行环境，请确认是否已安装Python")
                except Exception as e:
                    st.error(f"执行出错：{str(e)}")

# 在第二个标签页中
with tab2:
    st.header("素材管理")

    # 检查weibo目录是否存在
    weibo_dir = Path("weibo")
    if not weibo_dir.exists():
        st.info("暂无爬取数据，请先执行爬虫。")

        # 提供创建目录的选项
        if st.button("创建weibo目录"):
            try:
                weibo_dir.mkdir(exist_ok=True)
                st.success("weibo目录创建成功！")
                st.rerun()
            except Exception as e:
                st.error(f"创建目录时出错：{str(e)}")
    else:
        # 显示用户文件夹
        user_folders = [f for f in weibo_dir.iterdir() if f.is_dir()]
        folder_count = len(user_folders)

        if not user_folders:
            st.info("暂无用户数据文件夹。")
        else:
            # 添加刷新按钮
            if st.button("刷新数据"):
                st.rerun()

            selected_user = st.selectbox("选择用户文件夹", [f.name for f in user_folders])

            if selected_user:
                user_path = weibo_dir / selected_user

                # 显示文件信息
                st.subheader(f"文件信息：{selected_user}")

                # 显示文件列表
                files = list(user_path.rglob("*"))
                file_stats = []
                total_size = 0
                file_count = 0

                for file in files:
                    if file.is_file():
                        stat = file.stat()
                        size = stat.st_size
                        total_size += size
                        file_count += 1
                        file_stats.append({
                            "文件名": file.name,
                            "相对路径": str(file.relative_to(user_path)),
                            "大小": f"{size / 1024:.2f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB",
                            "修改时间": stat.st_mtime
                        })

                # 显示统计信息
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("文件夹数量", folder_count)
                col2.metric("文件数量", file_count)
                col3.metric("总大小",
                            f"{total_size / (1024 * 1024):.2f} MB" if total_size > 1024 * 1024 else f"{total_size / 1024:.2f} KB")

                # 显示文件列表
                if file_stats:
                    st.write("文件列表:")
                    st.dataframe(file_stats, use_container_width=True)
                else:
                    st.info("该用户文件夹中暂无文件。")

                # 打包下载功能
                st.subheader("打包下载")
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("打包为ZIP文件", use_container_width=True):
                        zip_path = f"{selected_user}.zip"
                        with st.spinner("正在打包文件..."):
                            try:
                                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                    for file in files:
                                        if file.is_file():
                                            # 保持目录结构
                                            arcname = file.relative_to(
                                                weibo_dir.parent) if weibo_dir.parent != file.parent else file.name
                                            zipf.write(file, arcname)
                                st.session_state[f"zip_ready_{selected_user}"] = zip_path
                                st.success(f"打包完成: {zip_path}")
                            except Exception as e:
                                st.error(f"打包过程中出错：{str(e)}")

                with col2:
                    zip_key = f"zip_ready_{selected_user}"
                    if zip_key in st.session_state and os.path.exists(st.session_state[zip_key]):
                        zip_path = st.session_state[zip_key]
                        with open(zip_path, "rb") as f:
                            st.download_button(
                                label="下载ZIP文件",
                                data=f,
                                file_name=os.path.basename(zip_path),
                                mime="application/zip",
                                use_container_width=True
                            )

                # 清除数据功能
                st.subheader("数据操作")
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("清除该用户数据", type="primary", use_container_width=True):
                        st.session_state[f"confirm_delete_{selected_user}"] = True

                with col2:
                    if st.button("在文件资源管理器中打开", use_container_width=True):
                        try:
                            os.startfile(str(user_path))
                        except Exception as e:
                            st.error(f"打开文件夹时出错：{str(e)}")

                # 确认删除
                if st.session_state.get(f"confirm_delete_{selected_user}", False):
                    st.warning(f"确认要删除 {selected_user} 的所有数据吗？此操作不可恢复！")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("确认删除", type="primary"):
                            try:
                                shutil.rmtree(user_path)
                                st.success("数据已清除！")
                                # 清除确认状态
                                st.session_state[f"confirm_delete_{selected_user}"] = False
                                # 刷新页面
                                st.rerun()
                            except Exception as e:
                                st.error(f"清除数据时出错：{str(e)}")
                    with col2:
                        if st.button("取消"):
                            st.session_state[f"confirm_delete_{selected_user}"] = False
                            st.rerun()

# 页脚信息
# st.markdown("---")
# st.caption("微博爬虫管理界面 - 基于 dataabc/weibo-crawler 开发")
