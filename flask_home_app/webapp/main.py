from backend import create_app

def main():
    app = create_app()
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    main()
