import product_availability as pa
import product_config as pc

REPORT_TYPES = [ "remaining issues", "work in progress" ]

def availability_report(latest_availability_by_product, selected_report):
    result = []
    result.append(HTML_HEAD)
    result.append('<body>')
    result.append('<h1>Why Online Sales Not Growing?</h1>')
    selector = report_selector(selected_report)
    result.append(data_table(selector, latest_availability_by_product))
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
<center><div class="btn-group" data-toggle="buttons">
''' + ''.join(('''
  <label class="btn''' + (" active" if report_type == selected_report else "") + '''">
    <input type="radio" value="''' + report_type.replace(' ', '_') + '''" name="report_type" ''' + ('checked' if report_type == selected_report else '') +\
'''> <i class="fa fa-circle-o fa-2x"></i><i class="fa fa-dot-circle-o fa-2x"></i> <span>''' + report_type +  '''</span>
  </label>''') for report_type in REPORT_TYPES) + '''
</div></center>
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
    'configuration' : 'not setup',
    'availability' : 'not available',
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

def listing_row(brand, family, problem_class, problem, problem_detail, date_time):
    if not problem: problem = ''
    if not problem_detail: problem_detail = ''
    if (not problem_class) or ('' == problem_class): problem_class = 'competitive'
    problem_class_nickname = _problem_class_to_nickname.get(problem_class, problem_class)
    result = []
    result.append('''
									<tr data-status="''' + problem_class + '''">
										<td>
											<div class="ckbox">
												<input type="checkbox" id="checkbox1">
												<label for="checkbox1"></label>
											</div>
										</td>
										<td>
											<a href="javascript:;" class="star">
												<i class="glyphicon glyphicon-star"></i>
											</a>
										</td>
										<td>
											<div class="media">
												<a href="#" class="pull-left">
													<img src="https://s3.amazonaws.com/uifaces/faces/twitter/fffabs/128.jpg" class="media-photo">
												</a>
												<div class="media-body">
													<span class="media-meta pull-right">''' + date_time.strftime('%b %d, %I:%M %p') + '''</span>
													<h4 class="title">''')
    result.append(brand + ' : ' + family)
    result.append('''
														<span class="pull-right ''' + problem_class + '''">(''' + problem_class_nickname + ''')</span>
													</h4>''')
    result.append('''
													<p class="summary">''' + problem + ': ' + problem_detail + '''</p>
												</div>
											</div>
										</td>
									</tr>''')
    return '\n'.join(result)


def data_table(report_selector_text, availability_data):
    problem_classes = set(row.get('problem_class','') for row in availability_data.values())\
                      | set(_problem_class_to_button_type.keys()) \
                      | set(_problem_class_to_nickname.keys())
    problem_classes.discard('')
    problem_tuples = sorted([(_problem_class_to_nickname.get(x,x), x) for x in sorted(list(problem_classes))])
    problem_classes = [x[1] for x in problem_tuples]
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
''' + '\n'.join('<button type="button" class="btn ' + _problem_class_to_button_type.get(x, 'btn-link') + ' btn-filter" data-target="' + x + '">' + _problem_class_to_nickname.get(x, x) + '</button>' for x in problem_classes) + '''
								<button type="button" class="btn btn-default btn-filter" data-target="all">all</button>
							</div>
						</div>
						<div class="table-container">
							<table class="table table-filter">
								<tbody>
									<tr data-status="competitive">
										<td>
											<div class="ckbox">
												<input type="checkbox" id="checkbox1">
												<label for="checkbox1"></label>
											</div>
										</td>
										<td>
											<a href="javascript:;" class="star">
												<i class="glyphicon glyphicon-star"></i>
											</a>
										</td>
										<td>
											<div class="media">
												<a href="#" class="pull-left">
													<img src="https://s3.amazonaws.com/uifaces/faces/twitter/fffabs/128.jpg" class="media-photo">
												</a>
												<div class="media-body">
													<span class="media-meta pull-right">Febrero 13, 2016</span>
													<h4 class="title">
														Lorem Impsum
														<span class="pull-right competitive">(competitive)</span>
													</h4>
													<p class="summary">Ut enim ad minim veniam, quis nostrud exercitation...</p>
												</div>
											</div>
										</td>
									</tr>
''')

    for row in availability_data.values():
        result.append(listing_row(row[pc.FIELD_BRAND], row[pc.FIELD_FAMILY], row.get('problem_class', ''), row.get('problem', ''), row.get('problem_detail', ''), row['local_time']))
    
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
$(document).ready(function () {

	$('.star').on('click', function () {
      $(this).toggleClass('star-checked');
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
</script>
 ''')
    return '\n'.join(result)

HTML_HEAD = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Avaiability</title>
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
.table-filter tr td:first-child {
	width: 38px;
}
.table-filter tr td:nth-child(2) {
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
	display: block;
}
.table-filter .star.star-checked {
	color: #F0AD4E;
}
.table-filter .star:hover {
	color: #ccc;
}
.table-filter .star.star-checked:hover {
	color: #F0AD4E;
}
.table-filter .media-photo {
	width: 35px;
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
}



  </style>
<link href="//netdna.bootstrapcdn.com/font-awesome/4.0.3/css/font-awesome.min.css" rel="stylesheet">
</head>
'''
