from colorthief import ColorThief
import requests
from PIL import Image
import io
import asyncio
from typing import List, Optional

class ColorExtractor:
    """Utilitário para extrair cores dominantes de imagens."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    async def extract_colors_from_url(self, image_url: str, color_count: int = 3) -> List[str]:
        """
        Extrai cores dominantes de uma imagem via URL.
        
        Args:
            image_url: URL da imagem
            color_count: Número de cores para extrair
            
        Returns:
            Lista de cores em formato hexadecimal
        """
        try:
            if not image_url:
                return []
            
            # Baixar imagem em thread separada
            loop = asyncio.get_event_loop()
            image_data = await loop.run_in_executor(
                None,
                self._download_image,
                image_url
            )
            
            if not image_data:
                return []
            
            # Extrair cores em thread separada
            colors = await loop.run_in_executor(
                None,
                self._extract_colors_from_data,
                image_data,
                color_count
            )
            
            return colors
            
        except Exception as e:
            print(f"Erro ao extrair cores da URL {image_url}: {str(e)}")
            return []
    
    async def extract_colors_from_file(self, file_path: str, color_count: int = 3) -> List[str]:
        """
        Extrai cores dominantes de um arquivo de imagem local.
        
        Args:
            file_path: Caminho do arquivo de imagem
            color_count: Número de cores para extrair
            
        Returns:
            Lista de cores em formato hexadecimal
        """
        try:
            # Extrair cores em thread separada
            loop = asyncio.get_event_loop()
            colors = await loop.run_in_executor(
                None,
                self._extract_colors_from_file,
                file_path,
                color_count
            )
            
            return colors
            
        except Exception as e:
            print(f"Erro ao extrair cores do arquivo {file_path}: {str(e)}")
            return []
    
    def _download_image(self, image_url: str) -> Optional[bytes]:
        """
        Baixa uma imagem da URL.
        
        Args:
            image_url: URL da imagem
            
        Returns:
            Dados binários da imagem ou None se falhou
        """
        try:
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Verificar se é uma imagem válida
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                print(f"Tipo de conteúdo inválido: {content_type}")
                return None
            
            return response.content
            
        except Exception as e:
            print(f"Erro ao baixar imagem: {str(e)}")
            return None
    
    def _extract_colors_from_data(self, image_data: bytes, color_count: int) -> List[str]:
        """
        Extrai cores de dados binários de imagem.
        
        Args:
            image_data: Dados binários da imagem
            color_count: Número de cores para extrair
            
        Returns:
            Lista de cores em formato hexadecimal
        """
        try:
            # Abrir imagem com PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Converter para RGB se necessário
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Salvar temporariamente em memória para ColorThief
            img_io = io.BytesIO()
            image.save(img_io, format='JPEG')
            img_io.seek(0)
            
            # Extrair cores usando ColorThief
            color_thief = ColorThief(img_io)
            
            if color_count == 1:
                # Extrair cor dominante
                dominant_color = color_thief.get_color(quality=1)
                return [self._rgb_to_hex(dominant_color)]
            else:
                # Extrair paleta de cores
                palette = color_thief.get_palette(color_count=color_count, quality=1)
                return [self._rgb_to_hex(color) for color in palette]
            
        except Exception as e:
            print(f"Erro ao extrair cores dos dados: {str(e)}")
            return []
    
    def _extract_colors_from_file(self, file_path: str, color_count: int) -> List[str]:
        """
        Extrai cores de um arquivo de imagem local.
        
        Args:
            file_path: Caminho do arquivo
            color_count: Número de cores para extrair
            
        Returns:
            Lista de cores em formato hexadecimal
        """
        try:
            color_thief = ColorThief(file_path)
            
            if color_count == 1:
                # Extrair cor dominante
                dominant_color = color_thief.get_color(quality=1)
                return [self._rgb_to_hex(dominant_color)]
            else:
                # Extrair paleta de cores
                palette = color_thief.get_palette(color_count=color_count, quality=1)
                return [self._rgb_to_hex(color) for color in palette]
            
        except Exception as e:
            print(f"Erro ao extrair cores do arquivo: {str(e)}")
            return []
    
    def _rgb_to_hex(self, rgb_tuple: tuple) -> str:
        """
        Converte tupla RGB para formato hexadecimal.
        
        Args:
            rgb_tuple: Tupla (R, G, B)
            
        Returns:
            Cor em formato hexadecimal (ex: "#FF5733")
        """
        try:
            r, g, b = rgb_tuple
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            print(f"Erro ao converter RGB para hex: {str(e)}")
            return "#000000"
    
    def get_color_brightness(self, hex_color: str) -> float:
        """
        Calcula o brilho de uma cor.
        
        Args:
            hex_color: Cor em formato hexadecimal
            
        Returns:
            Valor de brilho (0.0 a 1.0)
        """
        try:
            # Remover # se presente
            hex_color = hex_color.lstrip('#')
            
            # Converter para RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Calcular brilho usando fórmula de luminância
            brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return brightness
            
        except Exception as e:
            print(f"Erro ao calcular brilho: {str(e)}")
            return 0.5
    
    def is_dark_color(self, hex_color: str, threshold: float = 0.5) -> bool:
        """
        Determina se uma cor é escura.
        
        Args:
            hex_color: Cor em formato hexadecimal
            threshold: Limite para considerar cor escura (0.0 a 1.0)
            
        Returns:
            True se a cor é escura, False caso contrário
        """
        brightness = self.get_color_brightness(hex_color)
        return brightness < threshold
    
    def get_contrast_color(self, hex_color: str) -> str:
        """
        Retorna uma cor de contraste (branco ou preto) para uma cor dada.
        
        Args:
            hex_color: Cor em formato hexadecimal
            
        Returns:
            "#FFFFFF" para cores escuras, "#000000" para cores claras
        """
        if self.is_dark_color(hex_color):
            return "#FFFFFF"
        else:
            return "#000000"
