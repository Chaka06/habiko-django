"""
Service d'intégration CinetPay pour les paiements
Utilise le SDK officiel CinetPay
"""
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from cinetpay_sdk.s_d_k import Cinetpay
    CINETPAY_SDK_AVAILABLE = True
except ImportError:
    CINETPAY_SDK_AVAILABLE = False
    logger.warning("CinetPay SDK non disponible. Installation: pip install -i https://test.pypi.org/simple/ cinetpay-sdk==0.1.1")


class CinetPayService:
    """Service pour gérer les paiements via CinetPay en utilisant le SDK officiel"""
    
    @staticmethod
    def get_client():
        """Crée et retourne un client CinetPay en mode production"""
        if not CINETPAY_SDK_AVAILABLE:
            raise ValueError("CinetPay SDK non installé. Exécutez: pip install -i https://test.pypi.org/simple/ cinetpay-sdk==0.1.1")
        
        api_key = getattr(settings, "CINETPAY_API_KEY", "") or ""
        site_id = getattr(settings, "CINETPAY_SITE_ID", "") or ""
        
        if not api_key or not site_id:
            missing = []
            if not site_id:
                missing.append("CINETPAY_SITE_ID")
            if not api_key:
                missing.append("CINETPAY_API_KEY")
            raise ValueError(
                f"Configuration CinetPay incomplète. Variables manquantes: {', '.join(missing)}"
            )
        
        # Créer le client CinetPay
        # Le SDK utilise automatiquement le mode production si les bonnes clés sont utilisées
        # Vérifier que ce ne sont pas des clés de test
        if 'test' in api_key.lower() or 'test' in site_id.lower():
            logger.warning("ATTENTION: Clés CinetPay semblent être en mode test. Vérifiez vos clés API de production.")
        
        client = Cinetpay(api_key, site_id)
        
        # Si le SDK supporte un paramètre mode, l'ajouter
        # Note: Le SDK Python peut ne pas avoir ce paramètre, mais on le tente
        try:
            # Certains SDKs ont un paramètre mode dans le constructeur ou une méthode setMode
            if hasattr(client, 'setMode'):
                client.setMode('PRODUCTION')
            elif hasattr(client, 'mode'):
                client.mode = 'PRODUCTION'
        except Exception as e:
            logger.debug(f"Impossible de définir le mode production explicitement: {e}")
            # Ce n'est pas grave, le SDK utilisera le mode basé sur les clés API
        
        return client
    
    @staticmethod
    def generate_transaction_id(user_id, transaction_id):
        """Génère un ID de transaction unique pour CinetPay"""
        return f"KIABA_{user_id}_{transaction_id}_{int(timezone.now().timestamp())}"

    @staticmethod
    def create_payment_link(transaction, amount, description):
        """Crée un lien de paiement CinetPay"""
        try:
            client = CinetPayService.get_client()
        except ValueError as e:
            raise ValueError(str(e))
        
        # Générer l'ID de transaction
        transaction_id = CinetPayService.generate_transaction_id(
            transaction.user_id,
            transaction.id
        )
        
        # Récupérer les URLs depuis les settings
        notify_url = getattr(
            settings,
            "CINETPAY_NOTIFY_URL",
            "https://ci-kiaba.com/accounts/payment/cinetpay/notify/"
        )
        return_url = getattr(
            settings,
            "CINETPAY_RETURN_URL",
            "https://ci-kiaba.com/accounts/payment/cinetpay/return/"
        )
        
        # Récupérer les informations utilisateur
        user = transaction.user
        customer_name = user.first_name or user.username
        customer_surname = user.last_name or ""
        
        # Préparer les données pour l'initialisation du paiement
        # Convertir le montant en entier (CinetPay attend un entier)
        amount_int = int(float(amount))
        
        # Vérifier que le montant est valide
        if amount_int <= 0:
            raise ValueError("Le montant doit être supérieur à 0")
        
        data = {
            'amount': amount_int,
            'currency': "XOF",  # FCFA
            'transaction_id': transaction_id,
            'description': description[:255] if description else "Paiement KIABA",
            'return_url': return_url,
            'notify_url': notify_url,
            'customer_name': customer_name[:50] if customer_name else "Client",
            'customer_surname': customer_surname[:50] if customer_surname else "",
        }
        
        # Logger les données (sans les URLs complètes pour la sécurité)
        logger.debug(f"Données paiement: amount={data['amount']}, currency={data['currency']}, transaction_id={data['transaction_id']}")
        
        try:
            # Logger les données envoyées (sans les clés sensibles)
            logger.info(f"Initialisation paiement CinetPay - Transaction ID: {transaction_id}, Montant: {data['amount']} XOF")
            
            # Initialiser le paiement via le SDK
            response = client.PaymentInitialization(data)
            
            # Logger la réponse complète pour déboguer
            logger.info(f"Réponse CinetPay: {response}")
            
            # Le SDK retourne généralement un dictionnaire avec 'code' et 'data'
            if isinstance(response, dict):
                code = response.get('code')
                # Vérifier différents codes de succès possibles
                if code in ['201', 201, '00', 0, '200', 200]:
                    # Sauvegarder l'ID de transaction CinetPay
                    transaction.cinetpay_transaction_id = transaction_id
                    transaction.save()
                    
                    # Retourner l'URL de paiement (plusieurs formats possibles)
                    payment_url = (
                        response.get('data', {}).get('payment_url') or
                        response.get('data', {}).get('url') or
                        response.get('payment_url') or
                        response.get('url') or
                        response.get('data')
                    )
                    
                    if payment_url and isinstance(payment_url, str) and payment_url.startswith('http'):
                        logger.info(f"URL de paiement générée: {payment_url[:50]}...")
                        return payment_url
                    else:
                        logger.error(f"URL de paiement non trouvée dans la réponse. Réponse complète: {response}")
                        raise ValueError("URL de paiement non trouvée dans la réponse CinetPay")
                else:
                    # Erreur retournée par CinetPay
                    error_msg = (
                        response.get('message') or
                        response.get('description') or
                        response.get('error') or
                        f"Code d'erreur: {code}"
                    )
                    logger.error(f"Erreur CinetPay - Code: {code}, Message: {error_msg}, Réponse complète: {response}")
                    raise ValueError(f"Erreur CinetPay: {error_msg}")
            elif isinstance(response, str):
                # Si la réponse est directement l'URL
                if response.startswith('http'):
                    transaction.cinetpay_transaction_id = transaction_id
                    transaction.save()
                    logger.info(f"URL de paiement reçue directement: {response[:50]}...")
                    return response
                else:
                    logger.error(f"Réponse CinetPay inattendue (string): {response}")
                    raise ValueError(f"Réponse CinetPay inattendue: {response}")
            else:
                logger.error(f"Type de réponse CinetPay inattendu: {type(response)}, Valeur: {response}")
                raise ValueError(f"Réponse CinetPay inattendue: {response}")
                    
        except ValueError as e:
            # Re-raise les ValueError (erreurs métier)
            raise
        except Exception as e:
            logger.error(f"Exception lors de l'initialisation du paiement CinetPay: {type(e).__name__}: {str(e)}", exc_info=True)
            raise ValueError(f"Erreur de connexion à CinetPay: {str(e)}")

    @staticmethod
    def verify_payment(cinetpay_transaction_id):
        """Vérifie le statut d'un paiement CinetPay"""
        try:
            client = CinetPayService.get_client()
        except ValueError as e:
            logger.error(f"Erreur de configuration CinetPay: {str(e)}")
            return None
        
        try:
            # Vérifier avec l'ID de transaction
            response = client.TransactionVerfication_trx(cinetpay_transaction_id)
            
            if isinstance(response, dict):
                if response.get('code') == '00' or response.get('code') == 0:
                    payment_data = response.get('data', {})
                    return {
                        "status": payment_data.get("status"),
                        "amount": payment_data.get("amount"),
                        "currency": payment_data.get("currency"),
                        "payment_method": payment_data.get("payment_method"),
                    }
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du paiement CinetPay: {str(e)}")
            return None

    @staticmethod
    def verify_webhook_signature(data, signature):
        """Vérifie la signature d'un webhook CinetPay"""
        site_key = getattr(settings, "CINETPAY_SITE_KEY", "") or ""
        
        if not site_key:
            logger.warning("CINETPAY_SITE_KEY non configuré, impossible de vérifier la signature")
            return False
        
        # Construire la chaîne à signer selon la documentation CinetPay
        import hmac
        import hashlib
        
        signature_data = (
            f"{data.get('cpm_trans_id', '')}{site_key}"
            f"{data.get('cpm_amount', '')}{data.get('cpm_currency', 'XOF')}"
        )
        
        expected_signature = hmac.new(
            site_key.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
