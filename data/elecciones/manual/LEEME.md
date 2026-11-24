# Datos cargados a mano

`presidente_2023_cne.csv`: escrutinio definitivo de la elección presidencial 2023 (primera vuelta del 22/10 y balotaje del 19/11), votos por fórmula y por provincia. Transcripto de las tablas "Results by province, first round" y "second round" del artículo *2023 Argentine general election* de Wikipedia (que cita a la Cámara Nacional Electoral), consultado el 24/11/2026.

Controles al cargarlo (todos cierran): en cada provincia la suma de fórmulas + blancos y nulos da el total de votantes; la suma de las 24 provincias da el total nacional (1ra vuelta 27.623.920 votantes; balotaje 27.021.600); en el balotaje, la diferencia Milei − Massa coincide con el margen publicado en cada provincia.

La fila `(Blancos y nulos)` junta votos en blanco y nulos porque la tabla no los separa. Los electores habilitados se toman del escrutinio provisorio de la DINE (el padrón es el mismo).
