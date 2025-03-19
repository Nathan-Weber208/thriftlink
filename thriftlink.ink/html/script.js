$(document).ready(function () {
    // Login Form Submission
    $("#loginForm").submit(function (event) {
        event.preventDefault();
        $("#error").text(""); // Clear previous errors

        const email = $("#emailInput").val();
        const password = $("#passwordInput").val();

        $.ajax({
            type: "POST",
            url: "https://backend.thriftlink.ink/login",
            contentType: "application/json",
            data: JSON.stringify({ email, password }),
            success: function (response) {
                if (response.user_id) {
                    $("#loginButton").hide();
                    $("#successCheck").show();
                    // save the user_id, email, and password in local storage
                    localStorage.setItem("user_id", response.user_id);
                    localStorage.setItem("email", email);
                    localStorage.setItem("password", password);
                    
                } else {
                    $("#error").text("Invalid login credentials.");
                }
            },
            error: function () {
                $("#error").text("Login failed. Please check your details.");
            }
        });
    });

    // Toggle Create User Form
    $("#newUserLink").click(function (event) {
        event.preventDefault();
        $("#createUserForm").toggle();
    });

    // Create User Form Submission
    $("#createUserForm").submit(function (event) {
        event.preventDefault();
        $("#createError").text(""); // Clear previous errors

        const username = $("#usernameInput").val();
        const email = $("#newEmailInput").val();
        const password = $("#newPasswordInput").val();
        const confirmPassword = $("#confirmPasswordInput").val();

        if (password !== confirmPassword) {
            $("#createError").text("Passwords do not match.");
            return;
        }

        $.ajax({
            type: "POST",
            url: "https://backend.thriftlink.ink/createUser",
            contentType: "application/json",
            data: JSON.stringify({ username, email, password }),
            success: function (response) {
                if (response.success) {
                    alert("User created successfully! You can now log in.");
                    $("#createUserForm").hide();
                } else {
                    $("#createError").text("Failed to create user.");
                }
            },
            error: function () {
                $("#createError").text("Error creating user. Try again.");
            }
        });
    });
});