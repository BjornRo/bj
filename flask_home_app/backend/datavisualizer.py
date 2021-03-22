from flask import Blueprint, render_template, request, jsonify, url_for

datavisualizer = Blueprint('datavisualizer',__name__)


@datavisualizer.route("/")
def home():
    return ""