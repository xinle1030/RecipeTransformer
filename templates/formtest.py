$def with (form)

<html>
<head>
<title>Recipe Parser</title>
<style>
body {
    background-color: linen;
    font-family: sans-serif;
}

h1 {
    color: maroon;
    margin-top: 40px;
    margin-left: 40px;
} 

h3 {
  margin-left: 40px;
} 

form {
	position: absolute;
   top: 50%;
   left: 50%;
   transform: translate(-50%, -50%);
   text-align: right;
}

# label, input {
#     display: block;
# }

label {
    margin-top: 10px;
    margin-bottom: 30px;
}

div {
	margin: 0 auto;
	width: 600px;
	height: 200px;
	background-color: white;
	border: 1px black solid;
	position: relative;
}
.submit {
	margin-top: 1em;
  margin-right: 60px;
  border-radius: 4px;
}



</style>
</head>
<body>
	<h1>Recipe Parser</h1>
	<h3><em>Upload recipe files from AllHealthHubRecipes for parsing!</em><h3>
	<div>
    <form name="main" method="post" enctype="multipart/form-data" action="">
        $:form.render()
        <input type="submit" class="submit" />
    </form>
    </div>
</body>
</html>