document.addEventListener('DOMContentLoaded', () => {    
  function openModal($el) {
    $el.classList.add('is-active');   
    document.getElementById('workstationtext').focus();
    document.getElementById('OfficeDiag').focus();
    document.getElementById('TicketOffice').focus();
    document.getElementById('usernametext').focus();     
    document.getElementById('officetext').focus();
    document.getElementById('SOPofficetext').focus();
    document.getElementById('CADofficetext').focus();
    document.getElementById('NETofficetext').focus();
    document.getElementById('SOPworkstationtext').focus();        
    document.getElementById('AdminUsername').focus();       
         
  }

  function closeModal($el) {
    $el.classList.remove('is-active');
  }

  function closeAllModals() {
    (document.querySelectorAll('.modal') || []).forEach(($modal) => {
      closeModal($modal);
    });
  }

  (document.querySelectorAll('.js-modal-trigger') || []).forEach(($trigger) => {
    const modal = $trigger.dataset.target;
    const $target = document.getElementById(modal);

    $trigger.addEventListener('click', () => {
      //document.getElementById('hiddenScript').value = $trigger.getAttribute('data-scriptvalue'); 
      openModal($target);          
    });
  });

  (document.querySelectorAll('.modal-background, .modal-close, .modal-card-head .delete, .modal-card-foot .button') || []).forEach(($close) => {
    const $target = $close.closest('.modal');

    $close.addEventListener('click', () => {
      closeModal($target);
    });
  });

  document.addEventListener('keydown', (event) => {
    const e = event || window.event;

    if (e.keyCode === 27) { 
      closeAllModals();
    }
  });

  
});

function categorySwitch(){
  var selection = document.getElementById('NewTicketCategory').value;
  document.getElementById('SubCategory').classList.remove('is-hidden');
  document.getElementById('NewTicketSubCategory').value = '';
  document.getElementById('NewTicketItemCategory').value = '';

  if(selection == 'IT'){
    var rows = document.getElementsByClassName('IT'),
      len = rows !== null ? rows.length: 0,
      i = 0;
    for(i; i < len; i++){
      rows[i].classList.remove('is-hidden');
    };
    var rows = document.getElementsByClassName('Epic'),
      len = rows !== null ? rows.length: 0,
      i = 0;
    for(i; i < len; i++){
      rows[i].classList.add('is-hidden');
    };
  }else if(selection == 'Epic'){
    var rows = document.getElementsByClassName('IT'),
      len = rows !== null ? rows.length: 0,
      i = 0;
    for(i; i < len; i++){
      rows[i].classList.add('is-hidden');
    };
    var rows = document.getElementsByClassName('Epic'),
      len = rows !== null ? rows.length: 0,
      i = 0;
    for(i; i < len; i++){
      rows[i].classList.remove('is-hidden');
    };
  }
}

function subCategorySwitch(){

  var selection = document.getElementById('NewTicketSubCategory').value; 
  let stripped = selection.replace(/[^a-zA-Z0-9]/g, "");
  console.log(stripped);  
  document.getElementById('ItemCategory').classList.remove('is-hidden');
  document.getElementById('NewTicketItemCategory').value = '';

  var rows = document.getElementsByClassName('ItemCategory'),
      len = rows !== null ? rows.length: 0,
      i = 0;
  for(i; i < len; i++){
    rows[i].classList.add('is-hidden');
  };

  var rows = document.getElementsByClassName(stripped),
      len = rows !== null ? rows.length: 0,
      i = 0;
  for(i; i < len; i++){
    rows[i].classList.remove('is-hidden');
  };
}
function clearFilters(){
  var rows = document.getElementsByName('DepartmentCheckBox'),
    len = rows.length,
    i=0;
    for(i; i<len; i++){
      rows[i].checked=false;
    };
  var rows = document.getElementsByName('CategoryCheckBox'),
    len = rows.length,
    i=0;
    for(i; i<len; i++){
      rows[i].checked=false;
    };
}

function openUser(){
  document.getElementById('UserModal').classList.add('is-active');
  document.getElementById('usernametext').focus();
}

function NewTicket(){
  document.getElementById('NewTicketModal').classList.add('is-active');
}

function openUnlock(){
  document.getElementById('UnlockModal').classList.add('is-active');
  document.getElementById('adminUsername').focus();
}
function openPassword(){
  document.getElementById('PasswordModal').classList.add('is-active');
  document.getElementById('adminUsername').focus();
}
function passwordSubmit(){
  //document.getElementById("PasswordForm").submit();
}
function userSub(){
    document.getElementById("UserModal").classList.remove('is-active');
    document.getElementById("usersub").Disabled();
    //document.getElementById("UserForm").submit();
}
function unlockSubmit(){
  //document.getElementById("UnlockForm").submit();
}

function newTicketConfirm(){
  document.getElementById('TicketRouteModal').classList.add('is-active');
}

function filterModalActivate(){
  document.getElementById('filterModal').classList.add('is-active');
}

function dentistAlert() {
  document.getElementById('dentistModal').classList.add('is-active');    
}

function categorySelected() {
  document.getElementById('submitButton').removeAttribute("disabled");
}

function FilterCategorySwitch(){
  var switchCategory = document.getElementById('FilterSubCategory').value;
  if(switchCategory == 'Access/Password'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Asset Management'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Infrastructure'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Dental Imaging'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Computer Support'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'IT Operating Programs/Apps'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Network/Internet'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'PDS Enterprise Reporting'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Purchase New IT Equipment'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'QSI/CPS'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Unified Communications'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
  } else if(switchCategory == 'Wellfit'){
    selection = document.getElementsByClassName('AccessCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('AssetCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ComputerCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('DentalCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ProgramCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('InfraCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('NetworkCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('ReportingCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('EquipmentCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('CPSCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('UCCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.add('is-hidden');
    };
    selection = document.getElementsByClassName('WellfitCheckBox'),
      len = selection !== null ? selection.length: 0,
      i = 0;
    for(i;i<len;i++){
      selection[i].classList.remove('is-hidden');
    };
  }

}

function templateSwitch(){

  var choice = document.getElementById('TemplateChoice').value;  
  if(choice == 'None'){
    document.getElementById('Category').classList.remove('is-hidden');
    document.getElementById('SubCategory').classList.add('is-hidden');
    document.getElementById('ItemCategory').classList.add('is-hidden');
    document.getElementById('TemplatePlaceHolder').classList.add('is-hidden');
    document.getElementById('submitButton').disabled=true;
    document.getElementById('NewTicketDescription').value = '';
    document.getElementById('NewTicketSubject').value = '';
  }  
  else{
    document.getElementById('Category').classList.add('is-hidden');
    document.getElementById('SubCategory').classList.add('is-hidden');
    document.getElementById('ItemCategory').classList.add('is-hidden');
    document.getElementById('TemplatePlaceHolder').classList.remove('is-hidden');
  }
  if(choice == 'BYOD'){
    document.getElementById('NewTicketCategory').value = 'Epic';
    document.getElementById('NewTicketSubCategory').value = 'Epic - Back Office/Clinical';
    document.getElementById('NewTicketItemCategory').value = 'MyChart and Mobile Apps';
    document.getElementById('NewTicketSubject').value = 'Issues enrolling Mobile Device, BYOD';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketDescription').value = `Issues enrolling Mobile Device


MyChart, BYOD, Intune registration'


To register for BYOD, please use the following link: https://www.pdsconnect2.com/globalassets/departments/organizational-and-talent-development/content/job-aids/zfiles/people-services-center--how-to-request-mdm-program-enrollment.pdf

For instructions to register your mobile device
Android: https://www.pdsconnect2.com/contentassets/2bb731acb10d40c985e9301fd7b48396/uploaded-files/byod-enrollment-for-android-devices_638079012216983215.pdf

Apple: https://www.pdsconnect2.com/globalassets/departments/organizational-and-talent-development/content/job-aids/zfiles/byod-enrollment-for-ios-devices.pdf
    `;
    document.getElementById('submitButton').removeAttribute("disabled");
  
  } else if(choice == 'DentalImaging'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'Dental Imaging';
    document.getElementById('NewTicketItemCategory').value = '1VU';
    document.getElementById('NewTicketSubject').value = 'Please move x-rays in 1vu';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketDescription').value = `Please move x-rays in 1vu for office XXX from patient (MRN) to patient (MRN) for DOS XX/XX/XXXX. 

    Attached are the x-rays that need to be moved. 
    
    Thank you. 
    `;
    document.getElementById('submitButton').removeAttribute("disabled");
  

  } else if(choice == 'Circuit'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'Network';
    document.getElementById('NewTicketItemCategory').value = 'Circuits';
    document.getElementById('NewTicketSubject').value = 'Called to verify authorization for on site tech network work order';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketDescription').value = `Called to verify authorization for on site tech network work order
    `;
    document.getElementById('submitButton').removeAttribute("disabled"); 

  } else if(choice == 'Freshservice'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'IT Operating Programs/Apps';
    document.getElementById('NewTicketItemCategory').value = 'Freshservice';      
    document.getElementById('NewTicketPriority').value = '1';      
    document.getElementById('NewTicketSubject').value = '';
    document.getElementById('NewTicketDescription').value = '';
    document.getElementById('submitButton').removeAttribute("disabled");
    

  } else if(choice == 'ROC'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'IT Operating Programs/Apps';
    document.getElementById('NewTicketItemCategory').value = 'Eligibility System'; 
    document.getElementById('NewTicketSubject').value = 'HSC - DE Form Latency Issue (Onshore/Offshore)';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketDescription').value = `- Username

- DE link

- Description of what you/they were doing at the time of issue

- Time issue started

- Current issue delays and downtime

- Include snip of issue

- Copy/paste what you/they see here: Dental Eligibility Link (i.e. note server ID when launching) 
    `;
    document.getElementById('submitButton').removeAttribute("disabled");

  } else if(choice == 'EpicAccess'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'Access/Password';
    document.getElementById('NewTicketItemCategory').value = 'Epic Access';
    document.getElementById('NewTicketSubject').value = 'Epic Access Request';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketDescription').value = `User is requesting access in Epic to Office #
    `;
    document.getElementById('submitButton').removeAttribute("disabled");    

  } else if(choice == 'ITAccess'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'Access/Password'; 
    document.getElementById('NewTicketItemCategory').value = 'Add Provider Request';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketSubject').value = '';
    document.getElementById('NewTicketDescription').value = '';
    document.getElementById('submitButton').removeAttribute("disabled");    

  } else if(choice == 'PasswordReset'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'Access/Password';
    document.getElementById('NewTicketItemCategory').value = 'Unlock/Reset Account Password';
    document.getElementById('NewTicketSubject').value = 'Password Reset';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketDescription').value = `Password Reset Needed/Unlock accounts
    `;
    document.getElementById('submitButton').removeAttribute("disabled"); 

  } else if(choice == 'Wellfit'){
    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'Wellfit';
    document.getElementById('NewTicketItemCategory').value = 'Wellfit Escalation';      
    document.getElementById('NewTicketSubject').value = 'Wellfit Escalation Transfer';
    document.getElementById('NewTicketPriority').value = '1';
    document.getElementById('NewTicketDescription').value = `Wellfit Escalation Transfer
    `;
    document.getElementById('submitButton').removeAttribute("disabled"); 

  
  } else if(choice == 'TRE'){

    document.getElementById('NewTicketCategory').value = 'IT';
    document.getElementById('NewTicketSubCategory').value = 'Network/Internet';
    document.getElementById('NewTicketItemCategory').value = 'Network/WiFi Issue';
    document.getElementById('NewTicketSubject').value = 'Unable to log into computer';
    document.getElementById('NewTicketPriority').value = '2';
    document.getElementById('NewTicketDescription').value = `Unable to log into computer
Trust relationship Error
PC object not in or disabled in AD
    `;
    document.getElementById('submitButton').removeAttribute("disabled"); 
  
  };
}

function dateChange(){
  //document.getElementById('newDateForm').submit();
  document.getElementById('dateChangeButton').classList.remove('is-hidden');
}
function officeSearch(){
  document.getElementById('DiagnosticPageModal').classList.remove('is-active');
  document.getElementById('submitModal').classList.add('is-active');
  setTimeout(function(){
    document.getElementById('officeSearchForm').submit();
  }, 1000);    
}

function officeSearch2(){
  document.getElementById('submitModal').classList.add('is-active');
  setTimeout(function(){
    document.getElementById('officeSearchForm2').submit();
  }, 1000);        
}

function officeSearch3(){
  document.getElementById('submitModal').classList.add('is-active');
  setTimeout(function(){
    document.getElementById('officeSearchForm3').submit();
  }, 1000);        
}

function userSub(){      
  document.getElementById('UserModal').classList.remove('is-active');
  setTimeout(function(){        
      document.getElementById("UserForm").submit();
  }, 1000);
}