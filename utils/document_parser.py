"""
文档解析器模块
用于解析不同类型的文档并提取文本内容
"""
import os
import PyPDF2
import pdfplumber
import docx
import logging
import uuid
import shutil
import hashlib
import mammoth
from abc import ABC, abstractmethod
from PIL import Image
from io import BytesIO

class DocumentParser(ABC):
    """文档解析器抽象基类"""
    
    @abstractmethod
    def parse(self, file_path):
        """
        解析文档内容
        
        Args:
            file_path: 文档路径
            
        Returns:
            dict: 包含解析后的文本内容和元数据
        """
        pass
    
    @staticmethod
    def get_parser(file_path):
        """根据文件类型返回相应的解析器"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return PDFParser()
        elif ext == '.docx':
            return DocxParser()
        elif ext == '.txt':
            return TxtParser()
        else:
            raise ValueError(f"Unsupported file type: {ext}")


class PDFParser(DocumentParser):
    """PDF文档解析器"""
    
    def parse(self, file_path):
        """解析PDF文档内容"""
        text = ""
        metadata = {}
        
        try:
            # 使用PyPDF2提取元数据
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # 提取元数据
                if pdf_reader.metadata:
                    metadata = {
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                        'producer': pdf_reader.metadata.get('/Producer', ''),
                        'pages': len(pdf_reader.pages)
                    }
                
            # 使用pdfplumber提取文本（更准确）
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
                    
        except Exception as e:
            logging.error(f"Error parsing PDF file: {e}")
            raise
            
        return {
            'text': text.strip(),
            'metadata': metadata
        }


class DocxParser(DocumentParser):
    """DOCX文档解析器"""
    
    def _get_image_directory(self, file_path, doc_id=None):
        """
        获取文档图片存储目录
        
        Args:
            file_path: 文档路径
            doc_id: 文档ID（如果有）
            
        Returns:
            tuple: (图片目录路径, 图片URL路径)
        """
        # 获取静态文件夹路径
        static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
        
        # 根据文档ID或文件名生成唯一目录名
        if doc_id:
            dir_name = f'doc_{doc_id}'
        else:
            # 使用文件名的哈希值作为目录名
            file_hash = hashlib.md5(os.path.basename(file_path).encode()).hexdigest()
            dir_name = file_hash
        
        # 构建图片目录和URL路径
        image_dir = os.path.join(static_dir, 'doc_images', dir_name)
        image_url_path = f'/static/doc_images/{dir_name}'
        
        # 确保目录存在
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
            logging.info(f"创建图片目录: {image_dir}")
        else:
            logging.info(f"图片目录已存在: {image_dir}")
            
        return image_dir, image_url_path
    
    def _extract_images(self, doc, file_path, doc_id=None):
        """
        从DOCX文档中提取图片，包括尺寸信息
        
        Args:
            doc: python-docx Document对象
            file_path: 文档路径
            doc_id: 文档ID（如果有）
            
        Returns:
            dict: 图片关系ID到图片信息的映射
        """
        image_dir, image_url_path = self._get_image_directory(file_path, doc_id)
        logging.info(f"文档图片目录: {image_dir}")
        logging.info(f"文档图片URL路径: {image_url_path}")
        
        # 建立图片ID到URL的映射
        image_map = {}
        
        # 处理文档关系中的图片
        for rel in doc.part.rels.values():
            # 支持多种图片类型：常规图片和嵌入对象
            if rel.reltype == docx.opc.constants.RELATIONSHIP_TYPE.IMAGE:
                try:
                    image_blob = rel.target_part.blob
                    # 为图片生成唯一文件名
                    image_filename = f'image_{uuid.uuid4().hex}.png'
                    image_path = os.path.join(image_dir, image_filename)
                    image_url = f'{image_url_path}/{image_filename}'
                    
                    # 保存图片文件
                    with open(image_path, 'wb') as f:
                        f.write(image_blob)
                    
                    # 获取图片尺寸
                    width = None
                    height = None
                    try:
                        with Image.open(BytesIO(image_blob)) as img:
                            width, height = img.size
                            logging.info(f"图片尺寸: {width}x{height}")
                    except Exception as e:
                        logging.warning(f"无法获取图片尺寸: {e}")
                    
                    # 添加到映射，包含尺寸信息
                    image_map[rel.rId] = {
                        'url': image_url,
                        'path': image_path,
                        'width': width,
                        'height': height
                    }
                    logging.info(f"提取图片: {rel.rId} -> {image_url} ({width}x{height})")
                except Exception as e:
                    logging.error(f"提取图片失败 {rel.rId}: {e}")
                    continue
                
        logging.info(f"从文档中提取了 {len(image_map)} 个图片")
        return image_map
    
    def _extract_images_mammoth(self, file_path, doc_id=None):
        """
        使用mammoth提取DOCX文档中的图片
        
        Args:
            file_path: 文档路径
            doc_id: 文档ID（如果有）
            
        Returns:
            dict: 图片处理器，用于mammoth转换
        """
        image_dir, image_url_path = self._get_image_directory(file_path, doc_id)
        logging.info(f"Mammoth图片目录: {image_dir}")
        logging.info(f"Mammoth图片URL路径: {image_url_path}")
        
        # 图片计数器
        image_counter = [0]
        # 存储所有提取的图片路径，用于兜底展示
        extracted_images = []
        
        # 图片处理器
        def image_handler(image):
            # 为图片生成唯一文件名
            image_counter[0] += 1
            image_filename = f'image_mammoth_{uuid.uuid4().hex}_{image_counter[0]}.png'
            image_path = os.path.join(image_dir, image_filename)
            image_url = f'{image_url_path}/{image_filename}'
            
            # 保存图片文件 - 修复：完全读取图片数据后再写入文件
            try:
                # 读取图片数据
                with image.open() as image_data:
                    image_bytes = image_data.read()
                
                # 获取图片尺寸
                width = None
                height = None
                try:
                    with Image.open(BytesIO(image_bytes)) as img:
                        width, height = img.size
                        logging.info(f"Mammoth图片尺寸: {width}x{height}")
                except Exception as e:
                    logging.warning(f"无法获取Mammoth图片尺寸: {e}")
                
                # 将读取的图片数据写入文件
                with open(image_path, 'wb') as f:
                    f.write(image_bytes)
                
                logging.info(f"Mammoth提取图片: {image_filename} -> {image_url} ({width}x{height})")
                
                # 记录提取的图片
                extracted_images.append({
                    'url': image_url,
                    'width': width,
                    'height': height
                })
                
                # 返回图片URL和尺寸信息
                result = {'src': image_url}
                if width and height:
                    result['width'] = str(width)
                    result['height'] = str(height)
                return result
            except Exception as e:
                logging.error(f"Mammoth提取图片失败: {e}")
                return {'src': ''}
        
        # 返回图片处理器和提取的图片列表
        return image_handler, extracted_images
    
    def _convert_docx_to_html_mammoth(self, file_path, doc_id=None):
        """
        使用mammoth将DOCX转换为高保真HTML
        
        Args:
            file_path: 文档路径
            doc_id: 文档ID（如果有）
            
        Returns:
            str: 转换后的HTML内容
        """
        try:
            # 配置转换选项
            image_handler, extracted_images = self._extract_images_mammoth(file_path, doc_id)
            style_map = """
                p[style-name='Heading 1'] => h1:fresh
                p[style-name='Heading 2'] => h2:fresh
                p[style-name='Heading 3'] => h3:fresh
                p[style-name='Heading 4'] => h4:fresh
                p[style-name='Heading 5'] => h5:fresh
                p[style-name='Heading 6'] => h6:fresh
                r[style-name='Strong'] => strong
                r[style-name='Emphasis'] => em
                p[style-name='Quote'] => blockquote
                p[style-name='Intense Quote'] => blockquote.intense
                r[style-name='Underline'] => u
                p[style-name='List Paragraph'] => li
                table => table.table.table-bordered
            """
            
            # 转换DOCX为HTML
            with open(file_path, 'rb') as docx_file:
                result = mammoth.convert_to_html(
                    docx_file,
                    convert_image=mammoth.images.img_element(image_handler),
                    style_map=style_map
                )
            
            html = result.value
            messages = result.messages
            
            # 记录警告信息
            for message in messages:
                if message.type == "warning":
                    logging.warning(f"Mammoth警告: {message}")
            
            # 后处理HTML，为图片添加容器
            import re
            def wrap_images_with_container(html_content):
                # 匹配HTML中的img标签
                img_pattern = r'<img([^>]*)>'
                
                def replace_img(match):
                    img_tag = match.group(0)
                    # 将图片包装在容器中
                    return f'<div class="image-container">{img_tag}</div>'
                
                # 替换所有图片标签
                processed_html = re.sub(img_pattern, replace_img, html_content)
                return processed_html
            
            # 添加表格处理函数，将表格包装在可滚动容器中
            def wrap_tables_with_container(html_content):
                # 匹配HTML中的table标签
                table_pattern = r'<table([^>]*)>(.*?)</table>'
                
                def replace_table(match):
                    table_tag = match.group(0)
                    # 将表格包装在容器中
                    return f'<div class="table-container">{table_tag}</div>'
                
                # 替换所有表格标签
                processed_html = re.sub(table_pattern, replace_table, html_content, flags=re.DOTALL)
                return processed_html
            
            # 应用图片容器处理
            html = wrap_images_with_container(html)
            
            # 应用表格容器处理
            html = wrap_tables_with_container(html)
            
            # 添加兜底展示：如果有提取的图片但在HTML中找不到，在底部显示
            if extracted_images:
                # 检查HTML中是否包含所有提取的图片
                missing_images = []
                for img_info in extracted_images:
                    img_url = img_info['url']
                    if img_url not in html:
                        missing_images.append(img_info)
                
                # 如果有未在HTML中找到的图片，添加到底部
                if missing_images:
                    html += '<div class="document-images-fallback"><h3>文档中的其他图片</h3><div class="image-gallery">'
                    for img_info in missing_images:
                        width_attr = f' width="{img_info["width"]}"' if 'width' in img_info and img_info['width'] else ''
                        height_attr = f' height="{img_info["height"]}"' if 'height' in img_info and img_info['height'] else ''
                        html += f'<div class="image-item"><div class="image-container"><img src="{img_info["url"]}"{width_attr}{height_attr} alt="文档图片"></div><div class="image-caption">文档图片</div></div>'
                    html += '</div></div>'
            
            # 包装HTML，添加额外样式
            html = f"""
            <div class="docx-document mammoth-converted">
                <style>
                    .mammoth-converted table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
                    .mammoth-converted th, .mammoth-converted td {{ border: 1px solid #dee2e6; padding: 0.75rem; min-width: 60px; }}
                    .mammoth-converted img {{ max-width: 100%; height: auto; }}
                    .mammoth-converted blockquote {{ padding: 0.5rem 1rem; border-left: 5px solid #eee; }}
                    .mammoth-converted blockquote.intense {{ background-color: #f8f9fa; }}
                    .mammoth-converted h1, .mammoth-converted h2, .mammoth-converted h3 {{ margin-top: 1rem; margin-bottom: 0.5rem; }}
                    .document-images-fallback {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #dee2e6; }}
                    .image-gallery {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 1rem; }}
                    .image-item {{ width: auto; margin-bottom: 1rem; }}
                    .image-caption {{ font-size: 0.8rem; color: #6c757d; margin-top: 0.5rem; text-align: center; }}
                    .image-container {{ margin: 1rem 0; text-align: center; }}
                    .table-container {{ width: 100%; overflow-x: auto; margin-bottom: 1rem; }}
                </style>
                {html}
            </div>
            """
            
            logging.info(f"Mammoth成功转换文档: {file_path}, HTML长度: {len(html)}")
            return html
            
        except Exception as e:
            logging.error(f"Mammoth转换失败: {e}")
            raise
    
    def parse(self, file_path, doc_id=None):
        """解析DOCX文档内容，支持富文本格式和图片
        
        Args:
            file_path: 文档路径
            doc_id: 文档ID（如果有）
            
        Returns:
            dict: 包含文本内容、HTML内容和元数据的字典
        """
        text = ""
        html_content = ""
        metadata = {}
        
        try:
            doc = docx.Document(file_path)
            
            # 提取元数据
            core_properties = doc.core_properties
            metadata = {
                'title': core_properties.title or '',
                'author': core_properties.author or '',
                'subject': core_properties.subject or '',
                'created': str(core_properties.created) if core_properties.created else '',
                'modified': str(core_properties.modified) if core_properties.modified else '',
                'paragraphs': len(doc.paragraphs)
            }
            
            # 提取文本（用于搜索）
            for para in doc.paragraphs:
                text += para.text + "\n"
            
            # 使用mammoth生成高保真HTML
            html_content = self._convert_docx_to_html_mammoth(file_path, doc_id)
            
            # 保存图片目录信息，用于后续文档删除时清理
            image_dir, _ = self._get_image_directory(file_path, doc_id)
            metadata['image_directory'] = image_dir
                
        except Exception as e:
            logging.error(f"解析DOCX文件失败: {e}")
            raise
            
        return {
            'text': text.strip(),        # 纯文本用于搜索
            'html_content': html_content,  # HTML内容用于显示
            'metadata': metadata
        }


class TxtParser(DocumentParser):
    """TXT文档解析器"""
    
    def parse(self, file_path):
        """解析TXT文档内容"""
        text = ""
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(file_path, 'r', encoding='latin-1') as f:
                text = f.read()
        except Exception as e:
            logging.error(f"Error parsing TXT file: {e}")
            raise
            
        # TXT文件没有元数据，仅添加基本信息
        metadata = {
            'title': os.path.basename(file_path),
            'type': 'text/plain',
            'size': os.path.getsize(file_path)
        }
            
        return {
            'text': text.strip(),
            'metadata': metadata
        } 