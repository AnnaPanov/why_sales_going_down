import product_availability as pa
import product_config as pc

REPORT_TYPES = [ "remaining issues", "work in progress" ]

def availability_report(latest_availability_by_product, selected_report, username):
    result = []
    result.append(_html_head)
    result.append('<body>')
    #result.append('<h3>Low-Hanging Fruit &#x1f347;</h3><br><br>')
    #selector = report_selector(selected_report)
    result.append(data_table(latest_availability_by_product, "", username))
    if (username is None):
        result.append(_enter_username_popup)
    result.append('</body></html>')
    return ''.join(result)

def report_selector(report):
    selected_report = None
    if report:
        for r in REPORT_TYPES:
            if (r.replace(' ', '_') == report) or (r == report):
                selected_report = r
                break
    if not selected_report:
        selected_report = REPORT_TYPES[0]
    return '''
<center>
<div class="btn-group" data-toggle="buttons">
''' + ''.join(('''
  <label class="btn''' + (" active" if report_type == selected_report else "") + '''">
    <input type="radio" value="''' + report_type.replace(' ', '_') + '''" name="report_type" ''' + ('checked' if report_type == selected_report else '') +\
'''> <i class="fa fa-circle-o fa-2x"></i><i class="fa fa-dot-circle-o fa-2x"></i> <span>''' + report_type +  '''</span>
  </label>''') for report_type in REPORT_TYPES) + '''
</div>
</center>
<script>
function updateQueryStringParameter(uri, key, value) {
  var re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
  return uri.match(re) ? uri.replace(re, '$1' + key + "=" + value + '$2') : uri + (uri.indexOf('?') !== -1 ? "&" : "?") + key + "=" + value;
}
$(document).on("change","input[type=radio]",function(){
    var report_type_value=$('[name="report_type"]:checked').val();
    window.location.href = updateQueryStringParameter(window.location.href, 'report_type', report_type_value);
});
</script>
'''

_problem_class_to_nickname = {
    'competitive' : 'good',
    'configuration' : 'not setup',
    'availability' : 'out of stock',
    'reviews' : 'sad reviews',
    'assets' : 'wrong assets',
}
_problem_class_to_button_type = {
    'competitive' : 'btn-success',
    'availability' : 'btn-danger',
    'configuration' : 'btn-warning',
    'assets' : 'btn-seconary',
    'reviews' : 'btn-info',
}
_retailer_logos = {
    "macy's" : 'https://vignette1.wikia.nocookie.net/logopedia/images/b/b8/Macy%27s_Vertical_Logo.svg',
    "macys" : 'https://vignette1.wikia.nocookie.net/logopedia/images/b/b8/Macy%27s_Vertical_Logo.svg',
    "ulta" : 'https://logosave.com/images/large/common/02/ulta-beauty.png',
    "sephora" : 'http://www.parquecomercial-lacanada.com/sites/parquecomercial-lacanada.com/files/field/operador-logo/sephora_-_logo.jpg',
    "bloomingdales" : 'https://static.couponfollow.com/bloomingdales-com/logo.jpg',
    "nordstrom" : 'https://media.glassdoor.com/sqll/1704/nordstrom-squarelogo-1382998996505.png',
}

def listing_row(link, retailer, brand, family, problem_class, problem, problem_detail, date_time):
    additional_css = ('' if problem_class != '' else ' style="display:none"') # hide competitive stuff in the beginning
    if not problem: problem = ''
    if not problem_detail: problem_detail = ''
    if (not problem_class) or ('' == problem_class): problem_class = 'competitive'
    problem_class_nickname = _problem_class_to_nickname.get(problem_class, problem_class)
    retailer_logo_url = _retailer_logos.get(retailer.lower(), 'http://www.publicdomainpictures.net/pictures/40000/velka/question-mark.jpg')

    result = []
    result.append('''
									<tr data-status="''' + problem_class + '"' + additional_css + '''>
										<td>
											<div class="media">
												<a href="''' + link + '''" target=_blank class="pull-left">
													<img src="''' + retailer_logo_url + '''" class="media-photo" alt="''' + retailer + '''">
												</a>
												<div class="media-body">
													<span class="media-meta pull-right">''' + date_time.strftime('%b %d, %I:%M %p') + '''</span>
													<h4 class="title"><a class="title" href="''' + link + '''" target=_blank>''')
    result.append(brand + ' : ' + family)
    result.append('''
														</a><a href="''' + link + '''" target=_blank><span class="pull-right ''' + problem_class + '''">(''' + problem_class_nickname + ''')</span></a>
													</h4>''')
    result.append('''
													<p class="summary">''')
    if (problem or problem_detail):
        result.append(problem + ': ' + problem_detail)
    else: result.append('&#x2611;')
    result.append('''</p>
												</div>
											</div>
										</td>
										<td>
										<!--
                                                                                        <a class="star" href="#">&#127822;</a>
										-->
										<!--
											<div class="ckbox">
												<input type="checkbox" id="checkbox1">
												<label for="checkbox1"></label>
											</div>
											-->
										</td>
										<td>
<button title='remove from the list' class="btn btn-default btn-xs" data-title="Delete" data-toggle="modal" data-target="#delete">&#x1F5D9;</button>
										</td>										
									</tr>''')
    return '\n'.join(result)


def problem_class_count(availability_data, problem_class):
    if (problem_class == 'competitive'): problem_class = ''
    return sum(int(row['problem_class'] == problem_class) for row in availability_data.values())

def data_table(availability_data, report_selector_text, username):
    problem_classes = set(row.get('problem_class','') for row in availability_data.values())\
                      | set(_problem_class_to_button_type.keys()) \
                      | set(_problem_class_to_nickname.keys())
    problem_classes.discard('')
    problem_tuples = sorted([(_problem_class_to_nickname.get(x,x), x) for x in sorted(list(problem_classes))])
    problem_classes = [x[1] for x in problem_tuples]
    logout_button = ""
    if username:
        logout_button = '<button type="button" class="btn btn-default btn-sm" onclick="logout()" title="not ''' + username + ' anymore?" onlcick="logout"><span class="glyphicon glyphicon-log-out"></span> logout (' + username + ')</button>'
    result = []
    result.append('''
<!-- https://bootsnipp.com/snippets/featured/easy-table-filter -->
<div class="container">
		''' + report_selector_text + '''
	<div class="row">
		<section class="content">
			<div class="col-md-8 col-md-offset-2">
				<div class="panel panel-default">
					<div class="panel-body">
						<div class="pull-right">
							<div class="btn-group">
''' + '\n'.join('<button type="button" class="btn ' + _problem_class_to_button_type.get(x, 'btn-link') + ' btn-filter btn-sm" data-target="' + x + '">' + _problem_class_to_nickname.get(x, x) + ' (' + str(problem_class_count(availability_data, x)) + ')</button>' for x in problem_classes) + '''
								<button type="button" class="btn btn-default btn-filter btn-sm" data-target="all">all</button>''' + logout_button + '''
							</div>
						</div>
						<div class="table-container">
							<table class="table table-filter">
								<tbody>
''')
    for row in availability_data.values():
        result.append(listing_row(row[pc.FIELD_LINK],\
                                  row[pc.FIELD_RETAILER],\
                                  row[pc.FIELD_BRAND],\
                                  row[pc.FIELD_FAMILY],\
                                  row.get('problem_class', ''),\
                                  row.get('problem', ''),\
                                  row.get('problem_detail', ''),\
                                  row['local_time']))
    
    result.append('''								</tbody>
							</table>
						</div>
					</div>
				</div>
			</div>
		</section>		
	</div>
</div>
<script>
function validateForm() {
    var f = document.forms["resolvedForm"];
    var x = f["name"].value;
    if (x == "") {
        alert("'Who resolved the issue' must be filled out");
        return false;
    }
    f["original_url"].value = window.location.href;
    return true;
}
$(document).ready(function () {

    $('.star').on('click', function () {
      $(this).toggleClass('star-checked');
      $("#myModal").modal();
    });

    $('.ckbox label').on('click', function () {
      $(this).parents('tr').toggleClass('selected');
    });

    $('.btn-filter').on('click', function () {
      var $target = $(this).data('target');
      if ($target != 'all') {
        $('.table tr').css('display', 'none');
        $('.table tr[data-status="' + $target + '"]').fadeIn('slow');
      } else {
        $('.table tr').css('display', 'none').fadeIn('slow');
      }
    });

});
function logout() {
    var x = document.forms["logoutForm"];
    if (x) {
        x["follow"] = window.location.href    
        x.submit();
    }
}
</script>

<!-- the delete popup -->
    <div class="modal fade" id="delete" tabindex="-1" role="dialog" aria-labelledby="edit" aria-hidden="true">
      <div class="modal-dialog">
    <div class="modal-content" style="width:632px">
          <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-hidden="true"><span class="glyphicon glyphicon-remove" aria-hidden="true"></span></button>
        <h4 class="modal-title custom_align" id="Heading">Removing an SKU</h4>
      </div>
          <div class="modal-body">
       
       <div class="alert alert-danger"><span class="glyphicon glyphicon-warning-sign"></span>
       Are you sure?
       </div>
       
      </div>
      <div class="modal-footer " style="width:630px">
        <button type="button" class="btn btn-primary" ><span class="glyphicon glyphicon-ok-sign"></span> Yes (issue already addressed)</button>
        <button type="button" class="btn btn-info" ><span class="glyphicon glyphicon-ok-sign"></span> Yes Forever (SKU no longer needed)</button>
        <button type="button" class="btn btn-default" data-dismiss="modal"><span class="glyphicon glyphicon-remove"></span> No</button>
      </div>
        </div>
    <!-- /.modal-content --> 
  </div>
      <!-- /.modal-dialog --> 
    </div>

 ''')
    if username:
        result.append('''<form method="post" id="logoutForm"><input type="hidden" id="follow" name="follow"><input type="hidden" name="logout" value="''' + username + '''"></form>''')    
    return '\n'.join(result)

_html_head = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Low-Hanging Fruits</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
  <style>

label.btn span {
  font-size: 1.5em ;
}

label input[type="radio"] ~ i.fa.fa-circle-o{
    color: #c8c8c8;    display: inline;
}
label input[type="radio"] ~ i.fa.fa-dot-circle-o{
    display: none;
}
label input[type="radio"]:checked ~ i.fa.fa-circle-o{
    display: none;
}
label input[type="radio"]:checked ~ i.fa.fa-dot-circle-o{
    color: #7AA3CC;    display: inline;
}
label:hover input[type="radio"] ~ i.fa {
color: #7AA3CC;
}

label input[type="checkbox"] ~ i.fa.fa-square-o{
    color: #c8c8c8;    display: inline;
}
label input[type="checkbox"] ~ i.fa.fa-check-square-o{
    display: none;
}
label input[type="checkbox"]:checked ~ i.fa.fa-square-o{
    display: none;
}
label input[type="checkbox"]:checked ~ i.fa.fa-check-square-o{
    color: #7AA3CC;    display: inline;
}
label:hover input[type="checkbox"] ~ i.fa {
color: #7AA3CC;
}

div[data-toggle="buttons"] label.active{
    color: #7AA3CC;
}

div[data-toggle="buttons"] label {
display: inline-block;
padding: 6px 12px;
margin-bottom: 0;
font-size: 14px;
font-weight: normal;
line-height: 2em;
text-align: left;
white-space: nowrap;
vertical-align: top;
cursor: pointer;
background-color: none;
border: 0px solid 
#c8c8c8;
border-radius: 3px;
color: #c8c8c8;
-webkit-user-select: none;
-moz-user-select: none;
-ms-user-select: none;
-o-user-select: none;
user-select: none;
}

div[data-toggle="buttons"] label:hover {
color: #7AA3CC;
}

div[data-toggle="buttons"] label:active, div[data-toggle="buttons"] label.active {
-webkit-box-shadow: none;
box-shadow: none;
}  




/*    --------------------------------------------------
	:: General
	-------------------------------------------------- */
body {
	font-family: 'Open Sans', sans-serif;
	color: #353535;
}
h1 {
	text-align: center;
	color: navy;
}
.content h1 {
	text-align: center;
	color: navy;
}
.content .content-footer p {
	color: #6d6d6d;
    font-size: 12px;
    text-align: center;
}
.content .content-footer p a {
	color: inherit;
	font-weight: bold;
}

/*	--------------------------------------------------
	:: Table Filter
	-------------------------------------------------- */
.panel {
	border: 1px solid #ddd;
	background-color: #fcfcfc;
}
.panel .btn-group {
	margin: 15px 0 30px;
}
.panel .btn-group .btn {
	transition: background-color .3s ease;
}
.table-filter {
	background-color: #fff;
	border-bottom: 1px solid #eee;
}
.table-filter tbody tr:hover {
	cursor: pointer;
	background-color: #eee;
}
.table-filter tbody tr td {
	padding: 10px;
	vertical-align: middle;
	border-top-color: #eee;
}
.table-filter tbody tr.selected td {
	background-color: #eee;
}
.table-filter tr td:nth-child(2) {
	width: 35px;
}
.table-filter tr td:nth-child(3) {
	width: 35px;
}
.ckbox {
	position: relative;
}
.ckbox input[type="checkbox"] {
	opacity: 0;
}
.ckbox label {
	-webkit-user-select: none;
	-moz-user-select: none;
	-ms-user-select: none;
	user-select: none;
}
.ckbox label:before {
	content: '';
	top: 1px;
	left: 0;
	width: 18px;
	height: 18px;
	display: block;
	position: absolute;
	border-radius: 2px;
	border: 1px solid #bbb;
	background-color: #fff;
}
.ckbox input[type="checkbox"]:checked + label:before {
	border-color: #2BBCDE;
	background-color: #2BBCDE;
}
.ckbox input[type="checkbox"]:checked + label:after {
	top: 3px;
	left: 3.5px;
	content: '\e013';
	color: #fff;
	font-size: 11px;
	font-family: 'Glyphicons Halflings';
	position: absolute;
}
.table-filter .star {
	color: #ccc;
	text-align: center;
	font-weight: bold;
	display: block;
}
.table-filter .star.star-checked {
	color: #F0AD4E;
}
.table-filter .star:hover {
	color: #2BBCDE;
	text-decoration: none;
}
.table-filter .star.star-checked:hover {
	color: #F0AD4E;
}
.table-filter .media-photo {
	width: 35px;
	border:1px solid silver;
}
.table-filter .media-body {
    /* display: block; */
    /* Had to use this style to force the div to expand (wasn't necessary with my bootstrap version 3.3.6) */
}
.table-filter .media-meta {
	font-size: 11px;
	color: #999;
}
.table-filter .media .title {
	color: #2BBCDE;
	font-size: 14px;
	font-weight: bold;
	line-height: normal;
	margin: 0;
}
.table-filter .media .title span {
	font-size: .8em;
	margin-right: 20px;
}
.table-filter .media .title span.competitive {
	color: #5cb85c;
}
.table-filter .media .title span.configuration {
	color: #f0ad4e;
}
.table-filter .media .title span.availability {
	color: #d9534f;
}
.table-filter .media .summary {
	font-size: 14px;
	color: gray;
}

.modal-header, .close {
      background-color: #6699ff;
      color:white !important;
      text-align: center;
      font-size: 30px;
}
.modal-footer {
      background-color: #f9f9f9;
}

  </style>
<link href="//netdna.bootstrapcdn.com/font-awesome/4.0.3/css/font-awesome.min.css" rel="stylesheet">
</head>
'''

_enter_username_popup = '''
  <!-- Modal -->
  <div class="modal fade" id="enterUserName" role="dialog">
    <div class="modal-dialog">
    
      <!-- Modal content-->
      <div class="modal-content">
        <div class="modal-header" style="padding:35px 50px;">
<!--
          <button type="button" class="close" data-dismiss="modal">&times;</button>
-->
          <h4 class="modal-header" style="font-size: 18pt"><span class="glyphicon glyphicon-comment"></span> Hi! Welcome to "Low-Hanging Fruits"<br></h4>
        </div>
        <div class="modal-body" style="padding:40px 50px;">
          <form name="introduction" role="form" method="post" onsubmit="return validateIntroduction()">
            <div class="form-group" style="align:left">
              <label for="username"> What Is Your Name?</label>
              <table><tr><td width='95%'>
              <input type="text" class="form-control pull-left" id="username" name="username" placeholder="enter anything you want, no password required">
              <input type="hidden" id="follow" name="follow">
              </td><td>
              <button type="submit" class="btn btn-primary pull-right" style="align:right"><span class="glyphicon glyphicon glyphicon-send"></span></button>
              <input type="submit" style="display:none">
              </td></tr></table>
            </div>
          </form>
<script>
function validateIntroduction() {
    var x = document.forms["introduction"]["username"].value;
    if (x == "") {
        alert("You can write anything you want. It doesn't have to be your real name");
	document.forms["introduction"]["username"].focus();
        return false;
    }
    document.forms["introduction"]["follow"] = window.location.href
    return true;
}
$(document).ready(function(){
    $("#enterUserName").modal();
});
</script>
        </div>
      </div>
      
    </div>
  </div>  
'''
