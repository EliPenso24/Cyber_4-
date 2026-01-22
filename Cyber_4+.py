"""
HTTP Server with Timing and Connection Information
Author: Barak Gonen and Nir Dweck, modified by Eli Penso
Purpose: HTTP server that includes timing and connection metadata in responses
I added more features to the header response:Date, Connection Type, Server and eve Response Time.
"""
import os
import socket
import logging
from datetime import datetime
import time

QUEUE_SIZE = 10
IP = '0.0.0.0'
PORT = 80
SOCKET_TIMEOUT = 2
WEBROOT = r"C:\WEBROOT"
DEFAULT_URL = '/index.html'

HTTP_RESPONSE_200 = "HTTP/1.1 200 OK\r\n"
HTTP_RESPONSE_302 = "HTTP/1.1 302 Found\r\nLocation: {}\r\n"
HTTP_RESPONSE_400 = "HTTP/1.1 400 Bad Request\r\n"
HTTP_RESPONSE_403 = "HTTP/1.1 403 Forbidden\r\n"
HTTP_RESPONSE_404 = "HTTP/1.1 404 Not Found\r\n"
HTTP_RESPONSE_500 = "HTTP/1.1 500 Internal Server Error\r\n"

CONTENT_TYPE_HTML = "Content-Type: text/html; charset=utf-8\r\n"
CONTENT_TYPE_JPG = "Content-Type: image/jpeg\r\n"
CONTENT_TYPE_CSS = "Content-Type: text/css\r\n"
CONTENT_TYPE_JS = "Content-Type: text/javascript; charset=UTF-8\r\n"
CONTENT_TYPE_TXT = "Content-Type: text/plain\r\n"
CONTENT_TYPE_ICO = "Content-Type: image/x-icon\r\n"
CONTENT_TYPE_GIF = "Content-Type: image/gif\r\n"
CONTENT_TYPE_PNG = "Content-Type: image/png\r\n"
HTTP_HEADER_END = "\r\n"

REDIRECTION_DICTIONARY = {
    '/moved/': '/',
}

BINARY_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.ico')
UPLOAD_FOLDER = WEBROOT + '/uploads/'

def get_current_timestamp():
    """
    Get current timestamp in HTTP date format (RFC 7231).
    Returns: str: Date in format "Day, DD Mon YYYY HH:MM:SS GMT"
    """
    from email.utils import formatdate
    return formatdate(timeval=None, localtime=False, usegmt=True)


def build_header(status, content_type, content_length, connection_type='close', response_time_ms=None):
    """
    Build the HTTP response header with timing and connection information.
    Args:
        status (str): HTTP status line (e.g., "HTTP/1.1 200 OK\r\n")
        content_type (str): Content-Type header
        content_length (int): Length of the response body in bytes
        connection_type (str): Connection type ('close' or 'keep-alive')
        response_time_ms (float): Response time in milliseconds
    Returns:
        str: Complete HTTP response header
    """
    header = status
    header += f"Date: {get_current_timestamp()}\r\n"
    header += f"Server: EliHTTP/1.0 (Python)\r\n"
    header += content_type
    header += f"Content-Length: {content_length}\r\n"
    header += f"Connection: {connection_type}\r\n"
    if response_time_ms is not None:
        header += f"X-Response-Time: {response_time_ms:.2f}ms\r\n"
    header += HTTP_HEADER_END
    return header


def get_file_data(file_name):
    """
    Read a file from WEBROOT and return its contents.
    Args:
        file_name (str): Requested file path relative to WEBROOT
    Returns:
        bytes or str: File content
    Raises:
        FileNotFoundError: If the file does not exist or path is invalid
    """
    full_path = os.path.join(WEBROOT, file_name.lstrip('/'))
    real_path = os.path.abspath(full_path)
    real_root = os.path.abspath(WEBROOT)

    if not real_path.startswith(real_root):
        logging.warning(f"Directory traversal attempt: {file_name}")
        raise FileNotFoundError()

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        logging.info(f"File not found: {file_name}")
        raise FileNotFoundError()

    _, ext = os.path.splitext(file_name.lower())
    if ext in BINARY_EXTENSIONS:
        with open(full_path, 'rb') as f:
            return f.read()
    else:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()


def get_uploaded_file(file_name):
    """
    Read an uploaded file from the upload folder.
    Args:
        file_name (str): Name of the uploaded file
    Returns:
        bytes: File content (always binary for images)
    Raises:
        FileNotFoundError: If the file does not exist
    """
    # Create upload folder if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # If no extension, try common image extensions
    if not os.path.splitext(file_name)[1]:
        for ext in ['.png', '.jpg', '.jpeg', '.gif']:
            test_name = file_name + ext
            test_path = os.path.join(UPLOAD_FOLDER, test_name)
            if os.path.exists(test_path) and os.path.isfile(test_path):
                file_name = test_name
                break

    full_path = os.path.join(UPLOAD_FOLDER, file_name)

    # Security: prevent directory traversal
    real_path = os.path.abspath(full_path)
    real_upload = os.path.abspath(UPLOAD_FOLDER)

    if not real_path.startswith(real_upload):
        logging.warning(f"Directory traversal attempt in upload: {file_name}")
        raise FileNotFoundError()

    if not os.path.exists(real_path) or not os.path.isfile(real_path):
        logging.info(f"Uploaded file not found: {file_name}")
        raise FileNotFoundError()

    # Always read as binary for images
    with open(real_path, 'rb') as f:
        return f.read()


def handle_client_request(resource, client_socket, start_time, body = None, method = 'GET'):
    """
    Handle a single client request and send response with timing information.
    Args:
        resource (str): The requested URI path
        client_socket (socket.socket): Client socket for sending the response
        start_time (float): Request start time (from time.time())
        method (str): HTTP method (GET or POST), default is 'GET'
        body (bytes or None): Request body data for POST requests, None for GET
    """
    uri = DEFAULT_URL if resource in ('', '/') else resource
    print(uri)
    logging.info(f"Handling request for URI: {uri}")
    path, params = parse_query_string(uri)

    # Calculate response time
    def send_with_timing(status, content_type, body1):
        response_time_ms1 = (time.time() - start_time) * 1000
        header = build_header(status, content_type, len(body1), 'close', response_time_ms1)
        client_socket.send(header.encode() + body1)
        logging.info(f"Response sent in {response_time_ms1:.2f}ms")

        # Calculate-next endpoint
    if path == '/calculate-next':
        if 'num' not in params:
            body = b"400 Bad Request - Missing 'num' parameter"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body)
            return

        try:
            num = int(params['num'])
            next_num = num + 1
            body = str(next_num).encode('utf-8')
            send_with_timing(HTTP_RESPONSE_200, CONTENT_TYPE_TXT, body)
            logging.info(f"calculate-next: {num} -> {next_num}")
            return
        except ValueError:
            body = b"400 Bad Request - 'num' must be a valid integer"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body)
            return

    if path == '/calculate-area':
        if 'height' not in params or 'width' not in params:
            body = b"400 Bad Request - Missing 'height' or 'width' parameter"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body)
            return

        try:
            height = float(params['height'])
            width = float(params['width'])
            area = height * width / 2.0
            body = str(area).encode('utf-8')
            send_with_timing(HTTP_RESPONSE_200, CONTENT_TYPE_TXT, body)
            logging.info(f"calculate-area: {height,width} -> {area}")
            return
        except ValueError:
            body = b"400 Bad Request - 'num' must be a valid integer"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body)
            return

    if path == '/upload':
        # Must be POST request
        if method != 'POST':
            body_response = b"400 Bad Request - upload requires POST method"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body_response)
            return
        # Check if file-name parameter exists
        if 'file-name' not in params:
            body_response = b"400 Bad Request - Missing 'file-name' parameter"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body_response)
            return

        # Check if body has data
        if not body or len(body) == 0:
            body_response = b"400 Bad Request - No file data in request body"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body_response)
            return

        file_name = params['file-name']

        try:
            # Create upload folder if it doesn't exist
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Extract actual file data from multipart body
            # For simple case, try to find the binary data after headers
            file_data = body

            # If it's multipart/form-data, extract the actual file content
            if b'Content-Type:' in body:
                # Find where the actual file data starts (after empty line)
                parts = body.split(b'\r\n\r\n', 1)
                if len(parts) > 1:
                    file_data = parts[1]
                    # Remove the boundary end marker if present
                    if b'\r\n--' in file_data:
                        file_data = file_data.rsplit(b'\r\n--', 1)[0]

            # Save the file
            file_path = os.path.join(UPLOAD_FOLDER, params['file-name'])
            with open(file_path, 'wb') as f:
                f.write(file_data)

            body_response = b"File uploaded successfully"
            send_with_timing(HTTP_RESPONSE_200, CONTENT_TYPE_TXT, body_response)
            logging.info(f"File uploaded: {file_name} ({len(file_data)} bytes)")
            return

        except Exception as e:
            logging.error(f"Upload error: {e}")
            body_response = b"500 Internal Server Error - Upload failed"
            send_with_timing(HTTP_RESPONSE_500, CONTENT_TYPE_TXT, body_response)
            return

    if path == '/image':
        # Check if image-name parameter exists
        if 'image-name' not in params:
            body_response = b"400 Bad Request - Missing 'image-name' parameter"
            send_with_timing(HTTP_RESPONSE_400, CONTENT_TYPE_TXT, body_response)
            return

        image_name = params['image-name']

        try:
            # Get the uploaded image
            image_data = get_uploaded_file(image_name)

            # Determine content type based on file extension
            _, ext = os.path.splitext(image_name.lower())
            content_types = {
                '.jpg': CONTENT_TYPE_JPG,
                '.jpeg': CONTENT_TYPE_JPG,
                '.png': CONTENT_TYPE_PNG,
                '.gif': CONTENT_TYPE_GIF,
                '.ico': CONTENT_TYPE_ICO
            }
            content_type = content_types.get(ext, CONTENT_TYPE_JPG)

            send_with_timing(HTTP_RESPONSE_200, content_type, image_data)
            logging.info(f"Served uploaded image: {image_name}")
            return
        except FileNotFoundError:
            body_response = b"404 Not Found - Image does not exist"
            send_with_timing(HTTP_RESPONSE_404, CONTENT_TYPE_TXT, body_response)
            return


    # Special URIs
    if uri == '/forbidden/':
        body = b"403 Forbidden"
        send_with_timing(HTTP_RESPONSE_403, CONTENT_TYPE_HTML, body)
        return

    if uri == '/error/':
        body = b"500 Internal Server Error"
        send_with_timing(HTTP_RESPONSE_500, CONTENT_TYPE_HTML, body)
        return

    if uri in REDIRECTION_DICTIONARY:
        redirect_to = REDIRECTION_DICTIONARY[uri]
        response_time_ms = (time.time() - start_time) * 1000
        redirect_response = HTTP_RESPONSE_302.format(redirect_to)
        redirect_response += f"Date: {get_current_timestamp()}\r\n"
        redirect_response += f"Server: EliHTTP/1.0 (Python)\r\n"
        redirect_response += f"X-Response-Time: {response_time_ms:.2f}ms\r\n"
        redirect_response += HTTP_HEADER_END
        client_socket.send(redirect_response.encode())
        logging.info(f"302 Redirect sent in {response_time_ms:.2f}ms")
        return

    try:
        data = get_file_data(uri)
        _, ext = os.path.splitext(uri.lower())
        content_types = {
            '.html': CONTENT_TYPE_HTML,
            '.jpg': CONTENT_TYPE_JPG,
            '.jpeg': CONTENT_TYPE_JPG,
            '.css': CONTENT_TYPE_CSS,
            '.js': CONTENT_TYPE_JS,
            '.txt': CONTENT_TYPE_TXT,
            '.ico': CONTENT_TYPE_ICO,
            '.gif': CONTENT_TYPE_GIF,
            '.png': CONTENT_TYPE_PNG
        }
        ct = content_types.get(ext, "Content-Type: application/octet-stream\r\n")
        body = data if isinstance(data, bytes) else data.encode('utf-8')
        send_with_timing(HTTP_RESPONSE_200, ct, body)
    except FileNotFoundError:
        body = b"404 Not Found"
        send_with_timing(HTTP_RESPONSE_404, CONTENT_TYPE_HTML, body)
    except PermissionError:
        body = b"403 Forbidden"
        send_with_timing(HTTP_RESPONSE_403, CONTENT_TYPE_HTML, body)
    except OSError:
        body = b"500 Internal Server Error"
        send_with_timing(HTTP_RESPONSE_500, CONTENT_TYPE_HTML, body)


def parse_query_string(uri):
    """
    Parse query string from URI and return dictionary of parameters.
    Args:
        uri (str): Full URI including query string (e.g., '/calculate-next?num=8')
    Returns:
        tuple: (path, params_dict)
        Example: ('/calculate-next', {'num': '8'})
    """
    if '?' not in uri:
        return uri, {}

    path, query = uri.split('?', 1)
    params = {}

    # Split by & to get individual parameters
    for param in query.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            params[key] = value
    return path, params

def validate_http_request(request):
    """
    Validate the format of an HTTP GET request.
    Args:
        request (str): Raw HTTP request string
    Returns:
        tuple(bool, str or None): (is_valid, requested_path)
    """
    try:
        lines = request.splitlines()
        if not lines:
            return False, None
        method, path, version = lines[0].split()
        if (method != 'GET' and method != 'POST') or not path.startswith('/') or version != 'HTTP/1.1':
            return False, None
        return True, path
    except (ValueError, IndexError):
        return False, None


def handle_client(client_socket, client_addr):
    """
    Handle a single client connection with timing.
    Args:
        client_socket (socket.socket): Connected client socket
        client_addr (tuple): Client address (IP, port)
    """
    start_time = time.time()
    connection_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Client connected: {client_addr[0]}:{client_addr[1]} at {connection_time}")
    client_socket.settimeout(SOCKET_TIMEOUT)

    try:
        # Read initial request headers
        client_request = client_socket.recv(4096).decode('utf-8', errors='ignore')
        if not client_request:
            return

        # Separate headers from potential body
        if '\r\n\r\n' in client_request:
            headers_part, body_part = client_request.split('\r\n\r\n', 1)
        else:
            headers_part = client_request
            body_part = ''

        valid_http, resource = validate_http_request(headers_part)
        if valid_http:
            # Check if this is a POST request
            request_method = headers_part.split()[0]

            if request_method == 'POST':
                # Extract Content-Length from headers
                content_length = 0
                for line in headers_part.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        content_length = int(line.split(':')[1].strip())
                        break

                # Read the full body (binary data)
                body_data = body_part.encode('latin-1')  # Convert back to bytes
                while len(body_data) < content_length:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    body_data += chunk

                handle_client_request(resource, client_socket, start_time, method=request_method, body=body_data)
            else:
                handle_client_request(resource, client_socket, start_time, method=request_method, body=None)
        else:
            response_time_ms = (time.time() - start_time) * 1000
            body = b"400 Bad Request"
            header = build_header(HTTP_RESPONSE_400, CONTENT_TYPE_HTML, len(body), 'close', response_time_ms)
            client_socket.send(header.encode() + body)
            logging.info(f"400 Bad Request sent in {response_time_ms:.2f}ms")
    except socket.timeout:
        logging.warning(f"Socket timeout for client {client_addr}")
    except Exception as e:
        logging.error(f"Unexpected error for client {client_addr}: {e}")
    finally:
        total_time = (time.time() - start_time) * 1000
        logging.info(f"Connection closed: {client_addr[0]}:{client_addr[1]} | Total time: {total_time:.2f}ms")
        client_socket.close()

def init_logs():
    """
    Initialize logging system with detailed format.
    """
    os.makedirs("LOGS", exist_ok=True)
    logging.basicConfig(
        filename='LOGS/server.log',
        filemode='w',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("=" * 60)
    logging.info("HTTP Server Started")
    logging.info(f"Server: EliHTTP/1.0")
    logging.info(f"Listening on {IP}:{PORT}")
    logging.info(f"WEBROOT: {WEBROOT}")
    logging.info("=" * 60)


def assertions():
    """Run internal sanity checks."""
    import tempfile, shutil

    # בדיקת Headers (איחוד בדיקות למבנה ה-Header החדש)
    h = build_header(HTTP_RESPONSE_200, CONTENT_TYPE_HTML, 100, 'close', 15.5)
    assert all(
        x in h for x in ["200 OK", "Content-Length: 100", "X-Response-Time: 15.50ms", "Date:", "Server: EliHTTP"])

    # בדיקת ולידציה (GET תקין, POST תקין, וגרסה/מתודה לא תקינה)
    assert validate_http_request("GET /index.html HTTP/1.1\r\n")[0] == True
    assert validate_http_request("POST /upload HTTP/1.1\r\n")[0] == True
    assert validate_http_request("GET /index.html HTTP/1.0\r\n")[0] == False
    assert validate_http_request("DELETE / HTTP/1.1\r\n")[0] == False

    # בדיקת Query String (נתיב ופרמטרים)
    path, params = parse_query_string('/calculate-area?height=10&width=5')
    assert path == '/calculate-area' and params == {'height': '10', 'width': '5'}
    assert parse_query_string('/image?image-name=alaska.jpg')[1]['image-name'] == 'alaska.jpg'

    # בדיקת אבטחה (Directory Traversal)
    real_upload = os.path.abspath(UPLOAD_FOLDER)
    malicious_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, "../../secret.txt"))
    assert not malicious_path.startswith(real_upload)

    # בדיקת קריאת קבצים (Webroot זמני)
    tmp_dir = tempfile.mkdtemp()
    old_webroot = WEBROOT
    try:
        globals()['WEBROOT'] = tmp_dir
        with open(os.path.join(tmp_dir, 'test.html'), 'w') as f:
            f.write('<html>Test</html>')
        assert get_file_data('/test.html') == '<html>Test</html>'
    finally:
        globals()['WEBROOT'] = old_webroot
        shutil.rmtree(tmp_dir)

    print("All internal assertions passed!")

def main():
    """
    Main server loop with connection tracking.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enable SO_REUSEADDR to avoid "Address already in use" error
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((IP, PORT))
        server_socket.listen(QUEUE_SIZE)
        print(f" EliHTTP/1.0 Server listening on {IP}:{PORT}")
        print(f" Serving files from: {WEBROOT}")
        print(f" Server started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        connection_count = 0
        while True:
            client_socket, client_addr = server_socket.accept()
            connection_count += 1
            print(f" Connection #{connection_count} from {client_addr[0]}:{client_addr[1]}")
            handle_client(client_socket, client_addr)
    except KeyboardInterrupt:
        print("\n\n Server stopped by user")
        logging.info("Server stopped by user (Ctrl+C)")
    finally:
        server_socket.close()
        logging.info("Server socket closed")
        print(" Server shut down gracefully")


if __name__ == '__main__':
    init_logs()
    assertions()
    main()