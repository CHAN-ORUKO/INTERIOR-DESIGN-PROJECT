from django.shortcuts import render

# Create your views here.
import json
import base64
import requests
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import DesignPackage, MpesaTransaction

def get_mpesa_access_token():
    """Generates an OAuth access token from Safaricom"""
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET))
    return response.json().get('access_token')


def index_view(request):
    """Renders the main interior design showcase page"""
    all_packages = DesignPackage.objects.all()
    return render(request, 'interior.html', {'packages':all_packages})

# 1. HOME VIEW (Only manages packages layout)
def index_view(request):
    all_packages = DesignPackage.objects.all()
    return render(request, 'interior.html', {'packages': all_packages})

#2. PACKAGES VIEW (This now holds the database loop)
def packages_view(request):
    all_packages = DesignPackage.objects.all()
    return render(request, 'packages.html', {'packages': all_packages})

# 3. ABOUT VIEW
def about_view(request):
    return render(request, 'about.html')

# 3. CONTACT VIEW (Handles message submission processing safely here)
def contact_view(request):
    if request.method == 'POST':
        client_name = request.POST.get('name')
        client_email = request.POST.get('email')
        client_message = request.POST.get('message')

        ContactInquiry.objects.create(
            name=client_name,
            email=client_email,
            message=client_message
        )
        # Redirect users to a clean state after submitting successfully
        return redirect('/contact/')

    return render(request, 'contact.html')

@csrf_exempt
def trigger_stk_push(request, package_id):
    """Triggers an STK Push prompt to the user's mobile device"""
    if request.method == "POST":
        package = get_object_or_404(DesignPackage, pk=package_id)
        raw_phone = request.POST.get('phone')

        # Normalize local numbers like 0712345678 to 254712345678
        if raw_phone.startswith('0'):
            phone = '254' + raw_phone[1:]
        else:
            phone = raw_phone

        access_token = get_mpesa_access_token()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode('utf-8')

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(package.price), 
            "PartyA": phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": f"DesignPkg{package.id}",
            "TransactionDesc": f"Payment for {package.title}"
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload, 
            headers=headers
        )
        
        res_data = response.json()

        if res_data.get("ResponseCode") == "0":
            MpesaTransaction.objects.create(
                phone_number=phone,
                amount=package.price,
                checkout_request_id=res_data.get("CheckoutRequestID"),
                status='PENDING'
            )
        
        return JsonResponse(res_data)

@csrf_exempt
def mpesa_callback(request):
    """Safaricom hits this URL asynchronously when user inputs PIN"""
    data = json.loads(request.body)
    callback = data['Body']['stkCallback']
    checkout_id = callback.get('CheckoutRequestID')
    result_code = callback.get('ResultCode')

    try:
        transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_id)
        if result_code == 0:
            metadata = callback['CallbackMetadata']['Item']
            receipt_number = next(item['Value'] for item in metadata if item['Name'] == 'MpesaReceiptNumber')
            transaction.mpesa_receipt = receipt_number
            transaction.status = 'COMPLETED'
        else:
            transaction.status = 'FAILED'
        transaction.save()
    except MpesaTransaction.DoesNotExist:
        pass

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Callback Processed"})

def about_view(request):
    return render(request, 'about.html')


from django.shortcuts import render, redirect
from .models import DesignPackage, ContactInquiry  # Ensure ContactInquiry model is imported!

def index_view(request):
    # Check if a user submitted the contact form
    if request.method == 'POST':
        client_name = request.POST.get('name')
        client_email = request.POST.get('email')
        client_message = request.POST.get('message')

        # Save data into the database table
        ContactInquiry.objects.create(
            name=client_name,
            email=client_email,
            message=client_message
        )
        # Refresh the page cleanly to prevent duplicate form submissions
        return redirect('/')

    # Normal layout processing (GET request)
    all_packages = DesignPackage.objects.all()
    return render(request, 'interior.html', {'packages': all_packages})