from flask import Blueprint, request, jsonify
from middleware.auth_partner import partner_required

api_bp = Blueprint("api_bp", __name__)

@api_bp.route("/v1/transfers", methods=["POST"])
@partner_required(permission="TRANSFER")
def transfer():
    data = request.json

    # simulation transaction
    return jsonify({
        "status": "SUCCESS",
        "transaction_id": "TX" + data["from_wallet"][:4]
    })


@api_bp.route("/v1/balance", methods=["GET"])
@partner_required(permission="BALANCE")
def balance():
    return jsonify({
        "balance": 10000
    })