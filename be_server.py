import csv
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from os.path import dirname, join, abspath
import sys
sys.path.insert(0, join(dirname(__file__), 'Hunyuan3D-2'))
import api_keys as a
print("importing modules")
from run_me import img_to_3d  # Shows Error (Red underline) in IDE but will work fine
print("importing modules completed")

# --- Configuration ---
CSV_FILE = 'submissions.csv'

# Your Gmail account credentials
SENDER_EMAIL = a.SENDER_EMAIL
SENDER_PASSWORD = a.SENDER_PASSWORD  # Use an App Password, not your regular password!

SUBJECT = 'Your 3D Mesh is ready!'
BODY = 'Please find the file attached for your review.'

def send_email_with_attachments(file_path, RECEIVER_EMAIL):
    """Sends an email with multiple attachments via the Gmail SMTP server."""

    # 1. Create the email message container
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = SUBJECT

    # Attach the email body text
    msg.attach(MIMEText(BODY, 'plain'))

    # 2. Attach the files
    try:
        filename = os.path.basename(file_path)
        # print("filename: ", filename)

        # Check if file exists and get size (optional size check)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"Attaching {filename} (Size: {file_size_mb:.2f} MB)")
            # Open the file in binary mode
        with open(file_path, 'rb') as attachment:
                # Determine the MIME type (e.g., application/pdf, image/jpeg)
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())

        # Encode the file contents in Base64
        encoders.encode_base64(part)

        # Add header with the filename
        part.add_header(
            'Content-Disposition',
            f"attachment; filename= {filename}",
        )

        # Attach the part to the message
        msg.attach(part)

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}. Skipping attachment.")

    except Exception as e:
        print(f"An error occurred while attaching {file_path}: {e}")


    # 3. Connect to the SMTP Server and Send
    try:
        print("Connecting to SMTP server...")
        # For Gmail: Use port 587 and start TLS encryption
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()

        # Log in to your account
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        print("Login successful. Sending email...")

        # Send the email
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        print("✅ Email successfully sent!")

    except smtplib.SMTPAuthenticationError:
        print("Authentication Error: The username or password was incorrect. Did you use an App Password?")
    except smtplib.SMTPException as e:
        print(f"SMTP Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'server' in locals() and server:
            server.quit()
            print("Connection closed.")

# --- Main Logic ---
def process_csv():
    rows = []
    fieldnames = []

    # 1. Read the CSV file
    try:
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            # Convert to list to iterate
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: '{CSV_FILE}' not found.")
        return

    updates_made = False

    # 2. Process the rows
    for row in rows:
        # Get current statuses (stripping whitespace to be safe)

        id = row['id']

        print("reading row no. : ",id)
        print(row)

        img_name = row['image_filename'].strip()

        name_without_ext = Path(img_name).stem
        filepath = f'static/meshes/{name_without_ext}.stl'

        anime_name = row['anime_name'].strip()
        mail_id = row['email_id'].strip()
        build_status = row['build_status'].strip()
        mail_status = row['mail_status'].strip()

        # Condition 1: If build is N -> Run Func 1, Update Build to Y

        if build_status == 'N':
            # name_without_ext = Path(img_name).stem
            print("calling fns 1")
            img_to_3d(img_name,name_without_ext)
            # filepath = f'static/meshes/{name_without_ext}.stl'
            print("fns 1 completed")
            row['build_status'] = 'Y'
            # Update the local variable so the next check sees the new status immediately
            build_status = 'Y'
            updates_made = True

        # Condition 2: If build is Y AND mail is N -> Run Func 2, Update Mail to Y
        if build_status == 'Y' and mail_status == 'N':
            print("calling fns 2 : send_email_with_attachments")
            send_email_with_attachments(filepath, mail_id)
            print("fns 2 : send_email_with_attachments Completed")
            row['mail_status'] = 'Y'
            updates_made = True

    # 3. Write the updated data back to the CSV
    if updates_made:
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSuccess: '{CSV_FILE}' has been updated.")
    else:
        print("\nNo pending tasks found. No changes made to CSV.")

if __name__ == "__main__":
    # Run the processor
    process_csv()