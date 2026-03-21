class MarkerDetectionService:

    @staticmethod
    def detect(products):
        markers = []

        for p in products:
            if p["name"] == "огурец":
                markers.append("низкий аллергенный риск")

        return markers
