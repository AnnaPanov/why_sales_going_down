import product_availability as pa
import product_config as pc
import product_problems as pp
import datetime as dt
import urllib.parse

def availability_report(product_config, listing_appearance, listing_status, username, retailer):
    result = []
    result.append(_html_head)
    result.append('<body>')
    #result.append('<h3>Low-Hanging Fruit &#x1f347;</h3><br><br>')
    modified_appearance = listing_status.modify_appearance(product_config, listing_appearance, dt.datetime.utcnow())
    result.append(data_table(modified_appearance.values, listing_appearance.distinct_retailers, username, retailer))
    if (username is None):
        result.append(_enter_username_popup)
    result.append('</body></html>')
    return ''.join(result)

def download_link(retailer):
    return ' <a href="/download?retailer=' + urllib.parse.quote_plus(retailer) + '"><span class="summary"><i class="btn-sm glyphicon glyphicon-download-alt"></i>' + retailer + '</span></a>'

def retailer_selector(distinct_retailers, retailer):
    selected_retailer = None
    for r in distinct_retailers:
        if (r == retailer):
            selected_retailer = r
            break
    choices = [ "all" ] + list(distinct_retailers)
    if not selected_retailer:
        selected_retailer = choices[0]
    return '''
<div class="btn-group btn-xs" data-toggle="buttons" style="margin-bottom:0px; margin-top:0px;">
''' + ''.join(('''
  <label class="btn''' + (" active" if retailer == selected_retailer else "") + '''">
    <input type="radio" value="''' + retailer + '''" name="retailer" ''' + ('checked' if retailer == selected_retailer else '') +\
'''> <i class="fa fa-circle-o fa-2x"></i><i class="fa fa-dot-circle-o fa-2x"></i> <span>''' + retailer + '''</span>
  </label>''') for retailer in choices) + '''
</div>
<script>
function updateQueryStringParameter(uri, key, value) {
  var re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
  return uri.match(re) ? uri.replace(re, '$1' + key + "=" + value + '$2') : uri + (uri.indexOf('?') !== -1 ? "&" : "?") + key + "=" + value;
}
$(document).on("change","input[type=radio]",function(){
    var retailer=$('[name="retailer"]:checked').val();
    retailer = encodeURIComponent(retailer);
    window.location.href = updateQueryStringParameter(window.location.href, 'retailer', retailer);
});
</script>
'''

_problem_class_to_nickname = {
    'competitive' : 'good',
    'configuration' : 'not setup',
    'availability' : 'not there',
    'reviews' : 'problems with reviews',
    #'assets' : 'wrong assets',
    'deleted' : '<span class="glyphicon glyphicon-trash" title="deleted"></span>',
}
_problem_class_to_button_type = {
    'competitive' : 'btn-success',
    'availability' : 'btn-danger',
    'configuration' : 'btn-warning',
    'reviews' : 'btn-info',
    #'assets' : 'btn-seconary',
    'deleted' : 'btn-default',
}
_retailer_logos = {
    "macy's" : 'https://vignette1.wikia.nocookie.net/logopedia/images/b/b8/Macy%27s_Vertical_Logo.svg',
    "macys" : 'https://vignette1.wikia.nocookie.net/logopedia/images/b/b8/Macy%27s_Vertical_Logo.svg',
    "ulta" : 'https://www.brandsoftheworld.com/sites/default/files/styles/logo-thumbnail/public/082013/ulta-logo.png',
    "sephora" : 'http://www.parquecomercial-lacanada.com/sites/parquecomercial-lacanada.com/files/field/operador-logo/sephora_-_logo.jpg',
    "sephora ca" : 'http://www.freepngimg.com/download/maple_leaf/3-2-canada-leaf-free-png-image.png',
    "dillards" : 'http://logos-download.com/wp-content/uploads/2016/11/Dillards_logo_small.png',    
    "bloomingdales" : 'https://static.couponfollow.com/bloomingdales-com/logo.jpg',
    "bloomingdale's" : 'https://static.couponfollow.com/bloomingdales-com/logo.jpg',
    "nordstrom" : 'https://media.glassdoor.com/sqll/1704/nordstrom-squarelogo-1382998996505.png',
    "bon-ton" : 'http://vignette2.wikia.nocookie.net/logopedia/images/5/51/The_Bon-Ton_logo.jpg/revision/latest?cb=20120420111734',
    "bonton" : 'http://vignette2.wikia.nocookie.net/logopedia/images/5/51/The_Bon-Ton_logo.jpg/revision/latest?cb=20120420111734',
    "bon ton" : 'http://vignette2.wikia.nocookie.net/logopedia/images/5/51/The_Bon-Ton_logo.jpg/revision/latest?cb=20120420111734',
    "belk" : 'https://upload.wikimedia.org/wikipedia/en/8/8c/Belk_logo_2010.svg',
    "neiman-marcus" : 'https://media.glassdoor.com/sqll/471/neiman-marcus-squarelogo.png',
    "neiman marcus" : 'https://media.glassdoor.com/sqll/471/neiman-marcus-squarelogo.png',
    "neimanmarcus" : 'https://media.glassdoor.com/sqll/471/neiman-marcus-squarelogo.png',
    "lord&taylor" : 'https://vignette3.wikia.nocookie.net/logopedia/images/9/92/Lord_and_Taylor.svg/revision/latest/scale-to-width-down/250?cb=20130610041547',
    "boscovs" : 'https://locations.boscovs.com/images/default_bio.png',
    "jc penney" : 'https://vignette2.wikia.nocookie.net/monsterhigh/images/3/31/Logo_-_JCPenney.jpg/revision/latest?cb=20121012161449',
    "jc penney/ sephora" : 'https://vignette2.wikia.nocookie.net/monsterhigh/images/3/31/Logo_-_JCPenney.jpg/revision/latest?cb=20121012161449',
}

def listing_row(link, retailer, brand, family, title, problem_class, problem, problem_detail, item_id, date_time, addressed, reopened):
    additional_css = ('' if (problem_class != '' and problem_class != 'deleted' and (not addressed)) else ' style="display:none"') # hide competitive stuff in the beginning
    if not problem: problem = ''
    if not problem_detail: problem_detail = ''
    if (not problem_class) or ('' == problem_class): problem_class = 'competitive'
    data_status = problem_class if not addressed else 'addressed'
    problem_class_nickname = _problem_class_to_nickname.get(problem_class, problem_class)
    item_info = ""
    if item_id and (problem_class == pp.PROBLEM_WITH_AVAILABILITY):
        item_info = " (" + item_id + ")"
    retailer_logo_url = _retailer_logos.get(retailer.lower(), 'http://www.free-icons-download.net/images/question-mark-logo-icon-76440.png')
    result = []
    result.append('''
									<tr data-status="''' + data_status + '"' + additional_css + '''>
										<td>
											<div class="media">
												<a href="''' + link + '''" target=_blank class="pull-left">
													<img src="''' + retailer_logo_url + '''" class="media-photo" alt="''' + retailer + '''">
												</a>
												<div class="media-body">
													<span class="media-meta pull-right">''' + date_time.strftime('%b %d, %I:%M %p') + '''</span>
													<h4 class="title"><a class="title" href="''' + link + '''" target=_blank>''')
    result.append(title)
    decoration = ""
    if (addressed):
        decoration = ' style="text-decoration: line-through;" title="' + addressed + '"'
    if (reopened):
        decoration = ' style="text-decoration: underline;" title="' + reopened + '"'
    result.append('</a><a href="' + link + '" target=_blank><span class="pull-right ' + problem_class + '"' + decoration + '>(' + problem_class_nickname + ')</span></a></h4>')
    result.append('''
													<p class="summary">''')
    if (problem or problem_detail):
        result.append(problem + item_info + ': ' + problem_detail)
    else: result.append('&#x2611; looking good!')
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
										<td>''')
    delete_button = '''<button title='remove from the list' class="btn btn-default btn-xs" data-title="Delete" data-toggle="modal" data-target="#delete" onclick='setDeleteId("''' + link + '''");'>x</button>'''
    if (addressed or (problem_class == 'deleted')):
        delete_button = '''<button title='re-open the issue back' class="btn btn-danger btn-xs" data-title="Reopen" data-toggle="modal" data-target="#reopen" onclick='setReopenId("''' + link + '''");'><span class="glyphicon glyphicon-arrow-left"></span></button>'''
    result.append(delete_button)
    result.append('''
										</td>										
									</tr>''')
    return '\n'.join(result)


def problem_class_count(listings, problem_class):
    if (problem_class == 'deleted'):
        return ""
    elif (problem_class == 'addressed'):
        result = sum(int('addressed' in row) for row in listings)
    else:
        if (problem_class == 'competitive'): problem_class = ''
        result = sum(int('addressed' not in row and row['problem_class'] == problem_class) for row in listings)
    return (" (" + str(result) + ")") if (0 < result) else ""


def data_table(appearance_data, distinct_retailers, username, retailer):
    retailer_selector_code = retailer_selector(distinct_retailers, retailer)
    listings = [ row for row in appearance_data.values() if (not retailer) or (retailer == "all") or (retailer == row[pc.FIELD_RETAILER]) ]
    problem_classes = set(row.get('problem_class','') for row in listings)\
                      | set(_problem_class_to_button_type.keys()) \
                      | set(_problem_class_to_nickname.keys())
    problem_classes.discard('')
    problem_classes.discard('deleted')
    problem_tuples = sorted([(_problem_class_to_nickname.get(x,x), x) for x in sorted(list(problem_classes))])
    problem_classes = [x[1] for x in problem_tuples]
    problem_classes.append('addressed')
    problem_classes.append('deleted')
    logout_button = ""
    if username:
        logout_button = '<button type="button" class="btn btn-default btn-sm" onclick="logout()" title="not ''' + username + ' anymore?" onlcick="logout"><span class="glyphicon glyphicon-log-out"></span> logout</button>'
    result = []
    result.append('''
<!-- https://bootsnipp.com/snippets/featured/easy-table-filter -->
<div class="container">
	<div class="row">
		<section class="content">
			<div class="col-md-8 col-md-offset-2">
				<div class="panel panel-default">
					<div class="panel-body">
						<div class="pull-right">
							<div class="btn-group">
''' + '\n'.join('<button type="button" class="btn ' + _problem_class_to_button_type.get(x, 'btn-link') + ' btn-filter btn-sm" data-target="' + x + '">' + _problem_class_to_nickname.get(x, x) + problem_class_count(listings, x) + '</button>' for x in problem_classes) + '''
								<button type="button" class="btn btn-default btn-filter btn-sm" data-target="all">all</button>
								''' + logout_button + '''
							</div>
						</div>
						<div class="table-container">
		''' + retailer_selector_code + '''
							<table class="table table-filter">
								<tbody>
''')
    for row in listings:
        listing_title = row.get(pc.FIELD_TITLE, None)
        if not listing_title:
            listing_title = row[pc.FIELD_BRAND] + ": " + row[pc.FIELD_FAMILY]
        result.append(listing_row(row[pc.FIELD_LINK],
                                  row[pc.FIELD_RETAILER],
                                  row[pc.FIELD_BRAND],
                                  row[pc.FIELD_FAMILY],
                                  listing_title,
                                  row.get('problem_class', ''),
                                  row.get('problem', ''),
                                  row.get('problem_detail', ''),
                                  row.get('item_id', ''),
                                  row['local_time'],
                                  row.get('addressed', None),
                                  row.get('re-opened', None)))
    
    result.append('''								</tbody>
							</table>
						</div>
					</div>
				</div>
''')
    result.append('Downloads:<br>' + '<br>'.join(download_link(retailer) for retailer in distinct_retailers))
    result.append('''				
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
        x["follow"].value = window.location.href
        x.submit();
    }
}
function setDeleteId(id) {
    var x = document.forms["deleteForm"];
    if (x) {
        x["deleteId"].value = id;
    } else {
        alert("deleteForm not found");
    }
}
function setReopenId(id) {
    var x = document.forms["reopenForm"];
    if (x) {
        x["reopenId"].value = id;
    } else {
        alert("reopenForm not found");
    }
}
function doDelete(forHowLong) {
    var x = document.forms["deleteForm"];
    if (x) {
        x["deleteForHowLong"].value = forHowLong
        x["follow"].value = window.location.href
        x.submit();
    } else {
        alert("deleteForm not found");
    }
}
function doReopen() {
    var x = document.forms["reopenForm"];
    if (x) {
        x["follow"].value = window.location.href
        x.submit();
    } else {
        alert("reopenForm not found");
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
        <button type="button" class="btn btn-primary" onclick="doDelete('for 7 days');"><span class="glyphicon glyphicon-ok-sign"></span> Yes (issue already addressed)</button>
        <button type="button" class="btn btn-info" onclick="doDelete('forever');"><span class="glyphicon glyphicon-ok-sign"></span> Yes Forever (SKU no longer needed)</button>
        <button type="button" class="btn btn-default" data-dismiss="modal"><span class="glyphicon glyphicon-remove"></span> No</button>
      </div>
    </div>
    <!-- /.modal-content --> 
  </div>
      <!-- /.modal-dialog --> 
    </div>

<!-- the "delete" form -->
<form method="post" id="deleteForm">
<input type="hidden" id="deleteForHowLong" name="deleteForHowLong">
<input type="hidden" id="deleteId" name="deleteId">
<input type="hidden" id="follow" name="follow">
</form>

<!-- the reopen popup -->
    <div class="modal fade" id="reopen" tabindex="-1" role="dialog" aria-labelledby="edit" aria-hidden="true">
      <div class="modal-dialog">
    <div class="modal-content" style="width:632px">
          <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-hidden="true"><span class="glyphicon glyphicon-arrow-left" aria-hidden="true"></span></button>
        <h4 class="modal-title custom_align" id="Heading">Reopening an Issue</h4>
      </div>
          <div class="modal-body">
       
       <div class="alert alert-danger"><span class="glyphicon glyphicon-warning-sign"></span>
       Are you sure that the issue/SKU has to be re-opened?
       </div>
       
      </div>
      <div class="modal-footer " style="width:630px">
        <button type="button" class="btn btn-primary" onclick="doReopen();"><span class="glyphicon glyphicon-ok-sign"></span> Yes, have to re-open the issue back</button>
        <button type="button" class="btn btn-default" data-dismiss="modal"><span class="glyphicon glyphicon-remove"></span> No</button>
      </div>
    </div>
    <!-- /.modal-content --> 
  </div>
      <!-- /.modal-dialog --> 
    </div>

<!-- the "reopen" form -->
<form method="post" id="reopenForm">
<input type="hidden" id="reopenId" name="reopenId">
<input type="hidden" id="follow" name="follow">
</form>

 ''')
    if username:
        result.append('''<form method="post" id="logoutForm"><input type="hidden" id="follow" name="follow"><input type="hidden" name="logout" value="''' + username + '''"></form>''')    
    return '\n'.join(result)

_html_head = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Low-Hanging Fruit: the things which we can easily improve</title>
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
	background-image: url("http://www.ecmag.com/sites/default/files/xml_uploads/unzipped/apple_branch_fruit_iStock_000005660685_Large_0.jpg");
	background-repeat: no-repeat;
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
          <h4 class="modal-header" style="font-size: 18pt"><span class="glyphicon glyphicon-comment"></span> Hi!<br></h4>
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
    document.forms["introduction"]["follow"].value = window.location.href;
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
