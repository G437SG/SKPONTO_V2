from flask import send_from_directory
import os

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    try:
        return send_from_directory(
            os.path.join(app.root_path, 'static', 'img'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )
    except:
        # Se não existir favicon, retorna 204 (No Content) em vez de 404
        from flask import Response
        return Response(status=204)
