from backend import create_app

def main():
    app = create_app()
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    #app.run(debug=True, use_reloader=False)
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=80)

if __name__ == "__main__":
    main()
