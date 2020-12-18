from r2a.ir2a import IR2A
from player.parser import *
import time
import numpy as np

class R2A_Bola(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.qi = []
        self.throughput = 0
        self.request_time = 0
        self.vM = 0

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()
        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # Adquire o tempo em que a mensagem será encaminhada para o ConnectionHandler, isto servirá para depois calcular o throughput
        self.request_time = time.perf_counter()
        
        # Parâmetro de controle definido pelo Bola para possibilitar troca entre o tamanho do buffer e desempenho
        V = (self.whiteboard.get_max_buffer_size() - 1) / (self.vM + 5)
        
        # Adquire uma lista do tamanho dos buffers durante a reprodução do vídeo
        buffers = self.whiteboard.get_playback_buffer_size()
        
        # Adquire uma lista com o índice de qualidade do vídeo durante sua reprodução
        playback_qi = self.whiteboard.get_playback_qi()
        
        # Quando o vídeo ainda não começar a reproduzir coloca o buffer como 0
        if not buffers:
            buffers = ([0, 0], [0, 0])
            
        # Seleciona o nível mais recente do buffer
        current_buffer = buffers[-1]
        
        m = 0
        
        # Escolhe entre os 20 índices de qualidade qual resulta no maior valor para m_candidate
        for i in range(20):
            utility = np.log(self.qi[i] / self.qi[0])
            m_candidate = (V * utility + V * 5 - current_buffer[1]) / self.qi[i]
            if m_candidate > m:
                m = m_candidate
                selected_qi = i
        
        if playback_qi:
            """
            Se o índice de qualidade escolhido for maior que o índice do segmento anterior começa a procura de um novo índice 
            tal que tenha tamanho menor ou igual ao throughput do segmento anterior ou do primeiro índice, dependendo de qual for o maior
            """
            if selected_qi > playback_qi[-1][1]:
                max = self.qi[0]
                m1 = 0
                if self.throughput >= self.qi[0]:
                    max = self.throughput
                for j in range(20):
                    if self.qi[j] <= max and m1 <= j:
                        m1 = j
                
                # O novo índice de qualidade estiver entre os antigos índices ele ganha um novo valor, caso contrário recebe o mesmo valor deles
                if m1 >= m:
                    m1 = selected_qi
                elif m1 < playback_qi[-1][1]:
                    m1 = playback_qi[-1][1]
                else:
                    m1 = m1 + 1
                
                selected_qi = m1
        
        msg.add_quality_id(self.qi[selected_qi])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        # Determina o tempo que durou entre a mensagem ser encaminhada para o ConnectionHandler e voltar
        t = time.perf_counter() - self.request_time
        
        # Determina o throughput sobre a requisição do segmento de vídeo
        self.throughput = msg.get_bit_length() / t
        
        # Determina o utilitário derivado pelo usuário ao visualizar o vídeo suposto pelo algoritmo Bola
        self.vM = np.log(msg.get_quality_id() / self.qi[0])
        
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
