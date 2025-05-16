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
from abc import ABC, abstractmethod

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
    
    def _get_image_directory(self, file_path):
        """
        为文档创建唯一的图片目录
        
        Args:
            file_path: 文档路径
            
        Returns:
            tuple: (图片目录路径, 相对于静态目录的URL路径)
        """
        # 从文件路径中提取基本名称
        file_basename = os.path.basename(file_path)
        # 使用文件名或生成一个唯一ID
        doc_id = os.path.splitext(file_basename)[0]
        
        # 设置图片目录路径
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        image_dir = os.path.join(static_dir, 'doc_images', doc_id)
        image_url_path = f'/static/doc_images/{doc_id}'
        
        # 确保目录存在
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
            
        return image_dir, image_url_path
    
    def _extract_images(self, doc, file_path):
        """
        从DOCX文档中提取图片
        
        Args:
            doc: python-docx Document对象
            file_path: 文档路径
            
        Returns:
            dict: 图片关系ID到图片URL的映射
        """
        image_dir, image_url_path = self._get_image_directory(file_path)
        logging.info(f"文档图片目录: {image_dir}")
        logging.info(f"文档图片URL路径: {image_url_path}")
        
        # 建立图片ID到URL的映射
        image_map = {}
        
        # 处理文档关系中的图片
        for rel in doc.part.rels.values():
            if rel.reltype == docx.opc.constants.RELATIONSHIP_TYPE.IMAGE:
                image_blob = rel.target_part.blob
                # 为图片生成唯一文件名
                image_filename = f'image_{uuid.uuid4().hex}.png'
                image_path = os.path.join(image_dir, image_filename)
                image_url = f'{image_url_path}/{image_filename}'
                
                # 保存图片文件
                with open(image_path, 'wb') as f:
                    f.write(image_blob)
                
                # 添加到映射
                image_map[rel.rId] = image_url
                logging.info(f"提取图片: {rel.rId} -> {image_url}")
                
        logging.info(f"从文档中提取了 {len(image_map)} 个图片")
        return image_map
    
    def parse(self, file_path):
        """解析DOCX文档内容，支持富文本格式和图片"""
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
            
            # 提取图片并获取映射
            image_map = self._extract_images(doc, file_path)
            
            # 生成HTML内容（用于显示）
            html_content = '<div class="docx-document">'
            
            # 添加标题
            if metadata['title']:
                html_content += f'<h1 class="document-title">{metadata["title"]}</h1>'
            
            # 处理文档内容
            for para in doc.paragraphs:
                if para.text.strip():
                    # 检查段落样式
                    style = ""
                    if para.style.name.startswith('Heading'):
                        level = para.style.name[-1]
                        html_content += f'<h{level}>{para.text}</h{level}>'
                    else:
                        # 处理段落中的图片
                        has_image = False
                        for run in para.runs:
                            for element in run._element:
                                if element.tag.endswith('drawing'):
                                    # 在段落中查找图片
                                    image_found = False
                                    xml_str = str(element)
                                    for rId in image_map:
                                        if rId in xml_str:
                                            img_url = image_map[rId]
                                            html_content += f'<p><img src="{img_url}" alt="文档图片" class="img-fluid"></p>'
                                            has_image = True
                                            image_found = True
                                            logging.info(f"在段落中找到图片: {rId} -> {img_url}")
                                            break
                                    
                                    if not image_found:
                                        logging.warning(f"段落中包含图片元素，但未找到对应的图片ID")
                        
                        # 如果段落中没有图片，则添加文本内容
                        if not has_image:
                            html_content += f'<p>{para.text}</p>'
                else:
                    html_content += '<p>&nbsp;</p>'  # 空段落
            
            # 处理表格
            for table in doc.tables:
                html_content += '<table class="table table-bordered table-sm my-3">'
                
                # 遍历行和单元格
                for i, row in enumerate(table.rows):
                    html_content += '<tr>'
                    
                    for cell in row.cells:
                        tag = 'th' if i == 0 else 'td'  # 第一行使用th
                        cell_text = ""
                        
                        # 获取单元格内容
                        for paragraph in cell.paragraphs:
                            if paragraph.text:
                                cell_text += paragraph.text + " "
                        
                        html_content += f'<{tag}>{cell_text.strip()}</{tag}>'
                    
                    html_content += '</tr>'
                
                html_content += '</table>'
            
            html_content += '</div>'
            
            # 记录是否生成了HTML内容和图片
            logging.info(f"文档 {os.path.basename(file_path)} 生成了HTML内容，长度: {len(html_content)}")
            logging.info(f"文档 {os.path.basename(file_path)} 包含 {len(image_map)} 个图片")
            
            # 保存图片目录信息，用于后续文档删除时清理
            metadata['image_directory'] = self._get_image_directory(file_path)[0]
                
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