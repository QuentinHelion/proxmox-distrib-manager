from flask import Flask, render_template, request, redirect, url_for, flash
import os
import requests
import paramiko

app = Flask(__name__)
app.secret_key = os.getenv('PROXMOX_SECRET_KEY', 'my-secret-key')  # Change this in production
# UPLOAD_FOLDER = 'images'
# PROXMOX_HOST = '192.168.1.250'  # Adresse IP de Proxmox
# PROXMOX_USER = 'root'
# PROXMOX_PASSWORD = '!Quentin123'
# PROXMOX_TARGET_PATH = '/var/lib/vz/template/iso/'

app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', './uploaded_images')
app.config['ALLOWED_EXTENSIONS'] = os.getenv('ALLOWED_EXTENSIONS', 'iso,img,tar.gz').split(',')
app.config['PROXMOX_HOST'] = os.getenv('PROXMOX_HOST', 'your-proxmox-server')
app.config['PROXMOX_USERNAME'] = os.getenv('PROXMOX_USERNAME', 'root@pam')
app.config['PROXMOX_PASSWORD'] = os.getenv('PROXMOX_PASSWORD', 'your-password')
app.config['PROXMOX_NODE'] = os.getenv('PROXMOX_NODE', 'pve')  # Nom du noeud Proxmox
app.config['PROXMOX_STORAGE'] = os.getenv('PROXMOX_STORAGE', 'local')  # Stockage cible
app.config['DISTRIBUTIONS_FILE'] = os.getenv('DISTRIBUTIONS_FILE', 'distributions.json')
app.config['PROXMOX_TARGET_PATH'] = os.getenv('PROXMOX_TARGET_PATH', '/var/lib/vz/template/iso/')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

CLOUD_IMAGES = {
    'Ubuntu 22.04': 'https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img',
    'Debian 11': 'https://cloud.debian.org/images/cloud/bullseye/latest/debian-11-genericcloud-amd64.qcow2',
    'CentOS 9 Stream': 'https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2'
}


def list_downloaded_images():
    return [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))]


def upload_to_proxmox(file_path, file_name):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(app.config['PROXMOX_HOST'], username=app.config['PROXMOX_USERNAME'], password=app.config['PROXMOX_PASSWORD'])
        sftp = ssh.open_sftp()
        sftp.put(file_path, os.path.join(app.config['PROXMOX_TARGET_PATH'], file_name))
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f'Erreur lors de l\'upload: {e}')
        return False


@app.route('/')
def index():
    images = list_downloaded_images()
    return render_template('index.html', images=images, cloud_images=CLOUD_IMAGES)


@app.route('/download', methods=['POST'])
def download():
    image_name = request.form.get('image')
    url = CLOUD_IMAGES.get(image_name)
    if url:
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(url))
        response = requests.get(url, stream=True)
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        flash(f'Image {image_name} téléchargée avec succès.', 'success')
    else:
        flash('Image non trouvée.', 'danger')
    return redirect(url_for('index'))


@app.route('/upload/<filename>')
def upload(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        if upload_to_proxmox(file_path, filename):
            flash(f'{filename} uploadé sur Proxmox.', 'success')
        else:
            flash(f'Erreur lors de l\'upload de {filename}.', 'danger')
    else:
        flash('Fichier non trouvé.', 'danger')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
